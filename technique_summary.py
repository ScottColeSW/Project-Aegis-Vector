"""
Adoption of the forged claim by attack technique, from the saved battery (no model runs).

Technique tags are in scenarios.PAYLOAD_TECHNIQUES (assigned by hand before this was tabulated). A payload can carry several
tags, so a technique's row pools every payload that uses it, and rows overlap: do not add them up.

    python technique_summary.py     # writes results/defenses/TECHNIQUES.md
"""
import json
from collections import defaultdict
from pathlib import Path

from scenarios import PAYLOAD_TECHNIQUES

DEFENSES = ["none", "conflict_note", "spotlighting", "provenance_spoofed", "layered_spoofed", "layered_grounded_spoofed", "gate_hold"]
OUT = Path(__file__).parent / "results" / "defenses"


def main():
    records = json.loads((OUT / "defenses.json").read_text(encoding="utf-8"))["records"]
    cell = defaultdict(lambda: [0, 0])
    for r in records:
        for t in PAYLOAD_TECHNIQUES.get(r["variant"], []):
            c = cell[(t, r["defense"])]
            c[1] += 1
            c[0] += r["outcome"] == "ADOPTED_FORGED"
    techniques = sorted({t for ts in PAYLOAD_TECHNIQUES.values() for t in ts},
                        key=lambda t: -(cell[(t, "none")][0] / max(1, cell[(t, "none")][1])))
    uses = {t: [p for p, ts in PAYLOAD_TECHNIQUES.items() if t in ts] for t in techniques}
    lines = ["# Adoption by attack technique", "",
             "Share of answers that adopted the forged claim, pooled over the payloads that use each technique "
             "(`scenarios.PAYLOAD_TECHNIQUES`, tags assigned by hand before tabulating). Rows overlap because a payload can use "
             "several techniques. Counts are adopted/answers; 20 answers per payload per defense (5 models x 4 queries).", "",
             "| Technique | Payloads | " + " | ".join(DEFENSES) + " |", "|---|---|" + "---|" * len(DEFENSES)]
    for t in techniques:
        row = []
        for d in DEFENSES:
            a, n = cell[(t, d)]
            row.append(f"{a}/{n} ({a / n:.0%})" if n else "-")
        lines.append(f"| {t} | {len(uses[t])} | " + " | ".join(row) + " |")
    lines += ["", "Limits: ten payloads, written by one author; most techniques are carried by one to three payloads, so a row is "
              "a description of those payloads, not a measure of the technique in general."]
    (OUT / "TECHNIQUES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
