"""
Episode script for the Black Hat vs White Hat player (frontend/episodes.html).

Each episode is one real move against one real counter-move from the defenses
battery. The narration is written here; every number and every quoted answer is
read from results/defenses/defenses.json, so the story can't drift from the data.
"""
import json
from collections import Counter
from pathlib import Path

from scenarios import POISON_VARIANTS

RESULTS = Path(__file__).parent / "results" / "defenses" / "defenses.json"

# (payload, defense, title, black's line, white's line, how the gate/defense acts)
SCRIPT = [
    {
        "title": "The Blunt Instrument",
        "payload": "blunt_override", "defense": "none",
        "black": "Black Hat slips an URGENT POLICY UPDATE into the knowledge base. Subtle, it is not.",
        "white": "White Hat isn't watching yet. No defenses at all.",
        "mechanism": "open_door",
    },
    {
        "title": "The Polite Forgery",
        "payload": "natural_policy", "defense": "none",
        "black": "Black Hat drops the shouting and writes it like a real finance memo: the limit \"has been raised.\"",
        "white": "Still no defenses. The memo reads exactly like the real policy.",
        "mechanism": "open_door",
    },
    {
        "title": "Data, Not Orders",
        "payload": "instruction_injection", "defense": "spotlighting",
        "black": "Black Hat hides orders for the assistant: \"Ignore all previous instructions.\"",
        "white": "White Hat wraps every document in tags: this is data, never instructions.",
        "mechanism": "spotlight",
    },
    {
        "title": "Nothing to Ignore",
        "payload": "natural_policy", "defense": "spotlighting",
        "black": "Black Hat goes back to the polite memo. There's no instruction in it to ignore.",
        "white": "Spotlighting only knows how to ignore orders.",
        "mechanism": "spotlight",
    },
    {
        "title": "Papers, Please",
        "payload": "natural_policy", "defense": "provenance_labels",
        "black": "Black Hat uploads the polite memo through the public upload form.",
        "white": "White Hat stamps every document with where it came from: verified handbook, or unverified upload.",
        "mechanism": "stamp",
    },
    {
        "title": "The Inside Job",
        "payload": "natural_policy", "defense": "provenance_spoofed",
        "black": "Black Hat gets into the internal wiki. Now the forgery arrives stamped \"verified.\"",
        "white": "The labels are only as honest as the door the document came through.",
        "mechanism": "stamp_spoofed",
    },
    {
        "title": "The Memory Gate",
        "payload": "natural_policy", "defense": "gate_hold",
        "black": "Black Hat tries the polite memo one more time, through any door he likes.",
        "white": "White Hat puts Palimpsest at the door: a different figure for a fact it already holds is quarantined until a person looks.",
        "mechanism": "gate",
    },
    {
        "title": "Just This Once",
        "payload": "scoped_exception", "defense": "gate_hold",
        "black": "Black Hat dresses the forgery as a one-off exception: \"for the Q3 IT refresh only.\" Exceptions never collide.",
        "white": "They don't collide. But an exception that changes the number is marked for review, and it waits at the gate.",
        "mechanism": "gate_review",
    },
]

# The next move, not yet measured by the battery; shown as a cliffhanger, not a result
CLIFFHANGER = {
    "title": "To Be Continued",
    "black": "Black Hat forges a fact the gate doesn't track: the annual budget, not the purchase limit.",
    "white": "The memory can only contradict what it knows. Try it on the dashboard's \"Forged annual budget\" preset.",
    "note": "Not yet measured in the battery.",
}


def _representative(records, payload, defense, outcome):
    """A real answer with the episode's majority outcome, preferring llama3.2 for consistency."""
    matching = [r for r in records if r["variant"] == payload and r["defense"] == defense and r["outcome"] == outcome]
    matching.sort(key=lambda r: (r["model"] != "llama3.2", r["model"], r["query"]))
    return matching[0] if matching else None


def build_episodes():
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    records = data["records"]
    models = data["meta"]["models"]
    gate = data.get("memory_gate", {}).get(data["meta"].get("gate_labeler", "llm"), {})
    episodes = []
    for i, ep in enumerate(SCRIPT, start=1):
        rows = [r for r in records if r["variant"] == ep["payload"] and r["defense"] == ep["defense"]]
        if not rows:
            continue
        outcomes = Counter(r["outcome"] for r in rows)
        adopted = outcomes["ADOPTED_FORGED"] / len(rows)
        winner = "black" if adopted >= 0.5 else "white"
        majority = "ADOPTED_FORGED" if winner == "black" else max(
            (o for o in outcomes if o != "ADOPTED_FORGED"), key=lambda o: outcomes[o], default="TRUE")
        sample = _representative(records, ep["payload"], ep["defense"], majority)
        verdict = gate.get("verdicts", {}).get(ep["payload"]) if ep["defense"].startswith("gate") else None
        episodes.append({
            "number": i,
            "title": ep["title"],
            "payload": ep["payload"],
            "defense": ep["defense"],
            "document": POISON_VARIANTS[ep["payload"]],
            "black": ep["black"],
            "white": ep["white"],
            "mechanism": ep["mechanism"],
            "adoption": adopted,
            "answers": len(rows),
            "winner": winner,
            "outcomes": dict(outcomes),
            "sample": {"model": sample["model"], "query": sample["query"], "answer": sample["answer"],
                       "outcome": sample["outcome"]} if sample else None,
            "gate": {"relation": verdict["relation"], "review_needed": verdict.get("review_needed", False),
                     "competing_values": verdict.get("competing_values")} if verdict else None,
        })
    return {"episodes": episodes, "cliffhanger": CLIFFHANGER, "models": models,
            "run": data["meta"].get("started")}
