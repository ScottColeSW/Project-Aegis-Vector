"""
Registry coverage: which verified documents state a figure that no registered fact protects.

    python coverage_report.py     # writes results/coverage/COVERAGE.md
"""
from pathlib import Path

from memory_gate import registry_coverage

OUT = Path(__file__).parent / "results" / "coverage"


def main():
    c = registry_coverage()
    lines = ["# Registry coverage", "",
             f"The memory gate can only collide a forgery with a registered fact. **{c['covered']} of {c['total']}** verified documents "
             "that state a figure are covered; the rest are facts a forgery can change without the gate seeing a conflict.", "",
             "## Covered", ""] + [f"- `{p['fact']}`: {p['text']}" for p in c["protected"]]
    lines += ["", "## Not covered", ""] + [f"- {t}" for t in c["unprotected"]]
    lines += ["", "Registering a fact is a human decision (`scenarios.FACT_DOMAINS`); whoever can register decides what the gate protects.", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "COVERAGE.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
