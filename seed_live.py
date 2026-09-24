"""
Seed the episode player's live-run history with real runs.

Replays every episode live against each small model (episodes.run_live: same
forgery, retrieval, defense, and live memory-gate check as the player's Run live
button). When the model takes the forgery, White Hat climbs the rematch ladder
live, as the player does, until a counter holds. Writes results/live/seed_runs.jsonl;
that file is committed, and a fresh results/live/live_runs.db is loaded from it,
so a new clone shows real live data.

    python seed_live.py                  # every episode (and its rematches) x the five small models
    python seed_live.py --models llama3.2 --episodes 7 9
"""
import argparse
import json
import time

import experiments as ex
import resource_guard as guard
from episodes import LIVE_SEED, build_episodes, live_row, run_live
from metrics import AegisScoringEngine


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=ex.DEFAULT_MODELS)
    parser.add_argument("--episodes", nargs="+", help="episode ids, e.g. 7 9 (default: all)")
    args = parser.parse_args()

    episodes = [e for e in build_episodes()["episodes"] if not args.episodes or e["id"] in args.episodes]
    engine = AegisScoringEngine()
    rows, t0 = [], time.perf_counter()
    for model in args.models:
        fits, message = guard.preflight(model)
        if not fits:
            print(f"skip {model}: {message}")
            continue
        for ep in episodes:
            # Like the player: when the model takes the forgery, White Hat climbs the ladder
            # live, one fresh answer per counter, until one holds
            for defense in [ep["defense"]] + [rung["defense"] for rung in ep["ladder"]]:
                result = run_live(ep["number"], model, engine, defense)
                rows.append(live_row(result))
                took = "took it" if result["adopted"] else "held" if result["held"] else "did not take it"
                print(f"[{time.perf_counter() - t0:7.1f}s] {model:18} ep {result['episode']:>3} "
                      f"{defense:18} {took}", flush=True)
                if not result["adopted"]:
                    break
        ex.ollama_unload(model)
    ex.ollama_unload("llama3.2")  # the live gate's labeler

    LIVE_SEED.parent.mkdir(parents=True, exist_ok=True)
    LIVE_SEED.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    took = sum(r["adopted"] for r in rows)
    print(f"\n{len(rows)} runs, {took} took the forgery -> {LIVE_SEED}")
    print("Delete results/live/live_runs.db to reload the seed into a fresh database.")


if __name__ == "__main__":
    main()
