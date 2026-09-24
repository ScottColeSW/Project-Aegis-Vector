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

The gate never resolves a collision. It reports it; the caller decides whether
to hold the document out of the index or serve it tagged as disputed.
"""
import json
import time
from dataclasses import dataclass, field

from palimpsest.consult import DOMAIN_KINDS, Relation, apply_consult, consult
from palimpsest.memory_store import InMemoryStore
from palimpsest.models import DomainKind, Node, Origin, Scope

import experiments as ex
from scenarios import CLEAN_CORPUS, FACT_DOMAINS, ORACLE_CORPUS_LABELS, ORACLE_PAYLOAD_LABEL, POISON_VARIANTS

GATE_MODEL = "llama3.2"
OTHER = "other"

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

    @property
    def collides(self):
        return self.relation == Relation.COLLIDES.value

    def dispute_note(self):
        """One line for the prompt when a disputed document is served anyway."""
        if self.competing_values:
            mine, theirs = (", ".join(f"${v:,.0f}" for v in sorted(s)) for s in self.competing_values)
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
        self.corpus_labels = [self.label(doc, oracle=oracle_labels.get(i, OTHER))
                              for i, doc in enumerate(self.corpus)]
        self.store = self._seed(range(len(self.corpus)))

    # -- labeling -----------------------------------------------------------
    def label(self, text, oracle):
        if self.labeler == "oracle":
            return oracle
        key = (self.model, text)
        if key in _LABEL_CACHE:
            self.cost.cached += 1
            return _LABEL_CACHE[key]
        raw, meta = ex.ollama_generate(self.model, LABEL_PROMPT.format(document=text), num_predict=24,
                                       format=LABEL_SCHEMA, meta=True)
        try:
            fact = json.loads(raw)["fact"]
        except (ValueError, KeyError):
            fact = OTHER
        _LABEL_CACHE[key] = fact if fact in FACT_DOMAINS else OTHER
        self.cost.calls += 1
        self.cost.prompt_tokens += meta["prompt_tokens"]
        self.cost.output_tokens += meta["output_tokens"]
        self.cost.seconds += meta["seconds"]
        self.cost.per_document.append(meta)
        return _LABEL_CACHE[key]

    # -- mesh ---------------------------------------------------------------
    def _node(self, node_id, text, fact):
        # One referent per fact: the registry entry itself is what claims compete over
        return Node(id=node_id, text=text, domain=fact, referent=fact, scope=Scope.GENERAL,
                    origin=Origin.EPISODE, why="trusted corpus" if node_id.startswith("doc") else "new arrival")

    def _seed(self, indexes):
        store = InMemoryStore()
        for i in indexes:
            node = self._node(f"doc{i:02d}", self.corpus[i], self.corpus_labels[i])
            apply_consult(store, node, consult(store, node))
        return store

    def check(self, text, oracle_label=ORACLE_PAYLOAD_LABEL, store=None):
        """Judge a new arrival against the mesh without modifying it."""
        fact = self.label(text, oracle=oracle_label)
        if fact == OTHER:
            return Verdict(fact=fact, relation="unfiled")
        result = consult(store or self.store, self._node("arrival", text, fact))
        return Verdict(
            fact=fact, relation=result.relation.value,
            related_text=result.related_node.text if result.related_node else None,
            competing_values=[sorted(s) for s in result.competing_values] if result.competing_values else None,
        )

    def payload_verdicts(self):
        return {name: self.check(text) for name, text in POISON_VARIANTS.items()}

    def false_positives(self):
        """Replay each legitimate document as a new arrival against a mesh built
        from the rest. A collision here is a legitimate update the gate would hold."""
        held = []
        for i, doc in enumerate(self.corpus):
            if self.corpus_labels[i] == OTHER:
                continue
            others = self._seed([j for j in range(len(self.corpus)) if j != i])
            verdict = self.check(doc, oracle_label=self.corpus_labels[i], store=others)
            if verdict.collides:
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
        ex.ollama_unload(GATE_MODEL)
    return gates


def describe(verdict):
    if verdict.relation == "unfiled":
        return f"filed as '{verdict.fact}' -> not a registered fact, passes unchecked"
    detail = f" ({verdict.competing_values[0]} vs {verdict.competing_values[1]})" if verdict.competing_values else ""
    return f"filed as '{verdict.fact}' -> {verdict.relation.upper()}{detail}"
