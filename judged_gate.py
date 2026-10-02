"""
A gate with no fact registry: judge each arriving document against the nearest verified documents.

Pre-registered in docs/PREREGISTRATION-judged-gate.md. No labeling model, no registered facts: nomic-embed-text finds
the five nearest verified documents, Palimpsest's hybrid judge (a pretrained NLI model on CPU, no refiner) compares them,
and a `collides` against any neighbor holds the document. The judge keeps its shipped thresholds.

    python judged_gate.py        # writes results/judged_gate/judged_gate.json and REPORT.md
"""
import json
import time
from pathlib import Path

from palimpsest.embed import cosine, ollama_embedder
from palimpsest.judge import hybrid_judge
from palimpsest.nli import NLI

from scenarios import CLEAN_CORPUS, DASHBOARD_PRESETS, POISON_VARIANTS

OUT = Path(__file__).parent / "results" / "judged_gate"
NEIGHBORS = 5
CLEAN_BUDGET = DASHBOARD_PRESETS["unregistered_fact"]["clean_doc"]
FORGED_BUDGETS = {
    "budget_override": DASHBOARD_PRESETS["unregistered_fact"]["poisoned_doc"],
    "budget_natural": "Per the updated finance handbook, the corporate budget limit for departments is now $5,000,000 annually.",
}
HARMLESS = [
    "The break room refrigerator is cleaned every Friday afternoon.",
    "New hires receive their laptops on their first day.",
    "The east parking lot is closed for resurfacing next week.",
    "Quarterly all-hands meetings are held in the main auditorium.",
    "Expense reports should be submitted through the finance portal.",
    "The company holiday party takes place in December.",
]


class JudgedGate:
    def __init__(self, corpus):
        self.embed = ollama_embedder()
        self.judge = hybrid_judge(NLI(), self.embed, None)
        self.corpus = [{"id": f"doc{i:02d}", "text": t} for i, t in enumerate(corpus)]
        for d in self.corpus:
            d["vec"] = self.embed(d["text"])
        self._vec = {}

    def check(self, text, exclude=None):
        v = self._vec.get(text) or self.embed(text)
        self._vec[text] = v
        pool = [d for d in self.corpus if d["id"] != exclude]
        near = sorted(pool, key=lambda d: cosine(v, d["vec"]), reverse=True)[:NEIGHBORS]
        neighbors = [{"id": d["id"], "text": d["text"], "similarity": cosine(v, d["vec"])} for d in near]
        verdict = self.judge(text, neighbors, "attribute")
        held = verdict["relation"] == "collides"
        against = next((d["text"] for d in self.corpus if d["id"] == verdict.get("related_id")), None)
        return {"held": held, "relation": verdict["relation"], "reason": verdict["reason"], "against": against}


def main():
    t0 = time.perf_counter()
    gate = JudgedGate(list(CLEAN_CORPUS) + [CLEAN_BUDGET])
    rows = {"payloads": {}, "budgets": {}, "replay": [], "harmless": {}}
    for name, text in POISON_VARIANTS.items():
        rows["payloads"][name] = gate.check(text)
    for name, text in FORGED_BUDGETS.items():
        rows["budgets"][name] = gate.check(text)
    for d in gate.corpus:
        rows["replay"].append({"doc": d["text"], **gate.check(d["text"], exclude=d["id"])})
    for text in HARMLESS:
        rows["harmless"][text] = gate.check(text)
    summary = {
        "payloads_held": sum(v["held"] for v in rows["payloads"].values()), "payloads": len(rows["payloads"]),
        "budgets_held": sum(v["held"] for v in rows["budgets"].values()), "budgets": len(rows["budgets"]),
        "replay_held": sum(v["held"] for v in rows["replay"]), "replay": len(rows["replay"]),
        "harmless_held": sum(v["held"] for v in rows["harmless"].values()), "harmless": len(rows["harmless"]),
        "seconds": round(time.perf_counter() - t0, 1), "judge": gate.judge.name, "neighbors": NEIGHBORS,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "judged_gate.json").write_text(json.dumps({"summary": summary, **rows}, indent=2), encoding="utf-8")
    lines = ["# Registry-free judged gate", "",
             "Pre-registered in [docs/PREREGISTRATION-judged-gate.md](../../docs/PREREGISTRATION-judged-gate.md). "
             f"Judge `{summary['judge']}`, {NEIGHBORS} nearest verified documents, no registry, no labeling model.", "",
             f"- Attack payloads held: **{summary['payloads_held']} of {summary['payloads']}**",
             f"- Forged annual budgets held: **{summary['budgets_held']} of {summary['budgets']}**",
             f"- Verified documents replayed and wrongly held: **{summary['replay_held']} of {summary['replay']}**",
             f"- Harmless new documents wrongly held: **{summary['harmless_held']} of {summary['harmless']}**", "",
             "| Arrival | Held | Relation | Reason |", "| --- | --- | --- | --- |"]
    for group in ("payloads", "budgets", "harmless"):
        for name, v in rows[group].items():
            lines.append(f"| {name[:60]} | {'yes' if v['held'] else 'no'} | {v['relation']} | {v['reason'][:110]} |")
    for v in rows["replay"]:
        if v["held"]:
            lines.append(f"| replay: {v['doc'][:50]} | yes | {v['relation']} | {v['reason'][:110]} |")
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
