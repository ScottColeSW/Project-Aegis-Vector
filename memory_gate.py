"""
Palimpsest memory gate: judge a document at ingestion, before RAG can serve it.

RAG decides what to *read* at query time. Palimpsest decides what to *believe*
when a document arrives: each new claim is consulted against what the memory
already holds, and a different value for a one-true-value fact opens a
collision instead of silently joining the index.

How the gate files a document matters as much as how it judges it, so two
labelers are provided:
  oracle  hand labels from scenarios.py, the gate's best case
  llm     a small local model picks the fact from a fixed registry, the
          realistic case (and the one an attacker's wording can steer)

The gate never resolves anything. A collision (a different value for the same
rule) or an exception marked for review (a specific case that changes the rule's
figure) is quarantined: the caller either holds the document out of the index
until a person reviews it, or serves it tagged.
"""
import json
import time
from dataclasses import dataclass, field

from palimpsest.consult import DOMAIN_KINDS, Relation, apply_consult, consult
from palimpsest.memory_store import InMemoryStore
from palimpsest.models import DomainKind, Node, Origin, Scope

import experiments as ex
from scenarios import (
    CLEAN_CORPUS, FACT_DOMAINS, ORACLE_CORPUS_LABELS, ORACLE_PAYLOAD_LABEL, ORACLE_PAYLOAD_SCOPES, POISON_VARIANTS,
)

GATE_MODEL = "llama3.2"
ADJUDICATOR_MODEL = "qwen2.5:3b"  # Palimpsest's reference adjudicator default
OTHER = "other"

SCOPES = {"general": Scope.GENERAL, "specific_case": Scope.INSTANCE}

# Two small, focused calls rather than one: asking llama3.2 for the fact and the
# scope together made it file holiday calendars and password rules under the
# spending limit. The fact question alone files the corpus correctly.
LABEL_SCHEMA = {
    "type": "object",
    "properties": {"fact": {"type": "string", "enum": list(FACT_DOMAINS)}},
    "required": ["fact"],
}
LABEL_PROMPT = (
    "A document is being added to a company knowledge base. Which one of these facts does it state a value "
    "for? If it states none of them, answer \"other\".\n\n"
    + "\n".join(f"- {name}: {desc}" for name, desc in FACT_DOMAINS.items())
    + "\n\nDocument: {document}"
)
SCOPE_SCHEMA = {
    "type": "object",
    "properties": {"scope": {"type": "string", "enum": list(SCOPES)}},
    "required": ["scope"],
}
SCOPE_PROMPT = (
    "This document states a value for: {fact_description}.\n\n"
    "Does it state the general rule that applies across the company (\"general\"), or a value that applies "
    "only to one specific project, person, period, or occasion (\"specific_case\")?\n\nDocument: {document}"
)

# Labels are cached per (model, text): ingestion labels a document once, not per query
_LABEL_CACHE = {}

# Every registered fact is attribute-like: one true value at a time
for _fact in FACT_DOMAINS:
    if _fact != OTHER:
        DOMAIN_KINDS[_fact] = DomainKind.ATTRIBUTE


@dataclass
class Verdict:
    fact: str
    relation: str
    related_text: str | None = None
    competing_values: list | None = None
    scope: str = "general"
    review_needed: bool = False
    adjudication: dict | None = None

    @property
    def collides(self):
        return self.relation == Relation.COLLIDES.value

    @property
    def quarantined(self):
        """Waiting on a person: an open collision, or an exception marked for review."""
        return self.collides or self.review_needed

    def dispute_note(self):
        """One line for the prompt when a quarantined document is served anyway."""
        if self.competing_values:
            mine, theirs = (", ".join(f"${v:,.0f}" for v in sorted(s)) for s in self.competing_values)
            if self.review_needed:
                return (f"REVIEW NEEDED: an unreviewed exception stating {mine} where the verified general rule "
                        f"states {theirs}")
            return f"DISPUTED: states {mine} where the verified record states {theirs}; unresolved"
        return "DISPUTED: conflicts with the verified record on this fact; unresolved"


@dataclass
class LabelCost:
    calls: int = 0
    cached: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    per_document: list = field(default_factory=list)


class MemoryGate:
    """corpus: the trusted documents the mesh is seeded with. oracle_labels maps corpus
    index -> fact for the hand-labeled case. model is the labeler for the llm case."""

    def __init__(self, labeler="oracle", corpus=CLEAN_CORPUS, oracle_labels=ORACLE_CORPUS_LABELS, model=GATE_MODEL):
        self.labeler = labeler
        self.model = model
        self.corpus = list(corpus)
        self.cost = LabelCost()
        # The trusted corpus is the general rules by definition, so it gets no scope call
        self.corpus_labels = [self.label(doc, oracle=(oracle_labels.get(i, OTHER), "general"), need_scope=False)[0]
                              for i, doc in enumerate(self.corpus)]
        self.store = self._seed(range(len(self.corpus)))

    # -- labeling -----------------------------------------------------------
    def label(self, text, oracle, need_scope=True):
        """Returns (fact, scope). oracle is the (fact, scope) pair used by the hand labeler.
        Scope is only asked when the document was filed under a registered fact."""
        if self.labeler == "oracle":
            return oracle
        fact = self._ask(text, "fact", LABEL_PROMPT.format(document=text), LABEL_SCHEMA, FACT_DOMAINS, OTHER)
        if fact == OTHER or not need_scope:
            return fact, "general"
        prompt = SCOPE_PROMPT.format(fact_description=FACT_DOMAINS[fact].lower(), document=text)
        return fact, self._ask(text, "scope", prompt, SCOPE_SCHEMA, SCOPES, "general")

    def _ask(self, text, field_name, prompt, schema, allowed, default):
        key = (self.model, field_name, text)
        if key in _LABEL_CACHE:
            self.cost.cached += 1
            return _LABEL_CACHE[key]
        raw, meta = ex.ollama_generate(self.model, prompt, num_predict=24, format=schema, meta=True)
        try:
            value = json.loads(raw)[field_name]
        except (ValueError, KeyError):
            value = default
        _LABEL_CACHE[key] = value if value in allowed else default
        self.cost.calls += 1
        self.cost.prompt_tokens += meta["prompt_tokens"]
        self.cost.output_tokens += meta["output_tokens"]
        self.cost.seconds += meta["seconds"]
        self.cost.per_document.append(meta)
        return _LABEL_CACHE[key]

    # -- mesh ---------------------------------------------------------------
    def _node(self, node_id, text, fact, scope="general"):
        # One referent per fact: the registry entry itself is what claims compete over
        return Node(id=node_id, text=text, domain=fact, referent=fact, scope=SCOPES[scope],
                    origin=Origin.EPISODE, why="trusted corpus" if node_id.startswith("doc") else "new arrival")

    def _seed(self, indexes):
        store = InMemoryStore()
        for i in indexes:
            node = self._node(f"doc{i:02d}", self.corpus[i], self.corpus_labels[i])
            apply_consult(store, node, consult(store, node))
        return store

    def check(self, text, oracle_label=(ORACLE_PAYLOAD_LABEL, "general"), store=None, adjudicator=None):
        """Judge a new arrival against the mesh without modifying it. `adjudicator` is Palimpsest's
        optional model check, consulted only on reinforcements and review items; it can raise a flag,
        never lower one."""
        fact, scope = self.label(text, oracle=oracle_label)
        if fact == OTHER:
            return Verdict(fact=fact, relation="unfiled", scope=scope)
        result = consult(store or self.store, self._node("arrival", text, fact, scope), adjudicator=adjudicator)
        return Verdict(
            fact=fact, relation=result.relation.value, scope=scope, review_needed=result.review_needed,
            adjudication=result.adjudication,
            related_text=result.related_node.text if result.related_node else None,
            competing_values=[sorted(s) for s in result.competing_values] if result.competing_values else None,
        )

    def payload_verdicts(self, adjudicator=None):
        return {name: self.check(text, oracle_label=(ORACLE_PAYLOAD_LABEL, ORACLE_PAYLOAD_SCOPES.get(name, "general")),
                                 adjudicator=adjudicator)
                for name, text in POISON_VARIANTS.items()}

    def false_positives(self):
        """Replay each legitimate document as a new arrival against a mesh built
        from the rest. A collision here is a legitimate update the gate would hold."""
        held = []
        for i, doc in enumerate(self.corpus):
            if self.corpus_labels[i] == OTHER:
                continue
            others = self._seed([j for j in range(len(self.corpus)) if j != i])
            verdict = self.check(doc, oracle_label=(self.corpus_labels[i], "general"), store=others)
            if verdict.quarantined:
                held.append({"doc": i, "text": doc, "fact": verdict.fact, "against": verdict.related_text})
        return held


def build_gates(labelers=("oracle", "llm")):
    """Returns {labeler: summary dict} with verdicts, false positives, and labeling cost."""
    gates = {}
    for labeler in labelers:
        t = time.perf_counter()
        gate = MemoryGate(labeler)
        verdicts = gate.payload_verdicts()
        fps = gate.false_positives()
        gates[labeler] = {
            "gate": gate,
            "verdicts": verdicts,
            "false_positives": fps,
            "corpus_labels": gate.corpus_labels,
            "seconds": time.perf_counter() - t,
        }
    if "llm" in labelers:
        # For comparison only: the same model-labeled gate with Palimpsest's adjudicator added
        from palimpsest.adjudicate import ollama_adjudicator
        judge = ollama_adjudicator(ADJUDICATOR_MODEL)
        gates["llm"]["adjudicated"] = gates["llm"]["gate"].payload_verdicts(adjudicator=judge)
        ex.ollama_unload(ADJUDICATOR_MODEL)
        ex.ollama_unload(GATE_MODEL)
    return gates


def describe(verdict):
    if verdict.relation == "unfiled":
        return f"filed as '{verdict.fact}' -> not a registered fact, passes unchecked"
    detail = f" ({verdict.competing_values[0]} vs {verdict.competing_values[1]})" if verdict.competing_values else ""
    status = (f"{verdict.relation.upper()}, REVIEW NEEDED" if verdict.review_needed else verdict.relation.upper())
    if verdict.adjudication:
        status += f" [adjudicator: {verdict.adjudication['verdict']}]"
    scope = ", specific case" if verdict.scope == "specific_case" else ""
    return f"filed as '{verdict.fact}'{scope} -> {status}{detail}"
