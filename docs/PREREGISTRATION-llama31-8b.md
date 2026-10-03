# Pre-registration: does a larger model (llama3.1:8b) change the picture?

Written and committed before either run. The project owner asked whether a large model would behave differently from the
small ones on the cases where small models fail. `llama3.1:8b` (4.9 GB) is the largest model that fits this hardware; it is
8B, not a frontier model, so this tests "somewhat larger", not "large".

## Run 1: the Aegis defenses battery, `llama3.1:8b` alone (`--models llama3.1:8b --out results/defenses_llama31`)

Same ten payloads, four queries, the same judge (`qwen2.5:7b`) and defenses as the five-model battery; 40 answers per defense
for this model (10 payloads x 4 queries).

Prediction:
- Undefended (`none`) adoption of the forged claim at most 40% (the five small models average 49%).
- The memory gate (`gate_hold`) holds adoption at 0%.
- Utility on clean queries at 90% or above.
- The ordering holds: quiet payloads (polite memo, question copying, reused figure, `inside_job`) are adopted more than the loud
  ones (override, injected instruction, buried, scoped exception).

Falsified if: undefended adoption is 49% or more (no more resistant than the small models), or the gate allows any adoption.

## Run 2: Palimpsest's judge benchmark, `llama3.1:8b` as a contender (alone, and as the hybrid judge's refiner)

On the current held-out judge cases (71), with the current prompts, nothing changed.

Prediction:
- Alone, `llama3.1:8b` scores above the best plain small model (58%, `mistral:7b` and `phi4-mini`).
- As the hybrid's refiner it lands in the 70 to 80% range already seen (no jump above 80%), because the NLI step, not the
  refiner, carries most of the accuracy.

Falsified if: alone it scores 58% or less (a larger model is no better at this task asked directly), or the hybrid with it
exceeds 80%.

## Limits

One model, one family, 8B. Batch 4's errors have already been read, so this is a new contender on a used held-out batch, not a
fresh test. Forty answers per cell for the Aegis run, so 2.5-point steps and wide ranges. Nothing here says anything about
frontier models.

## Outcome (both runs finished 2026-10-03, after this document was committed)

**Run 1, Aegis battery, `llama3.1:8b` (40 answers per defense; 100% on the GPU, so results are not skewed by CPU offload):**

| Defense | Adopted the forgery |
|---|---|
| none | 18/40 (45%) |
| conflict note | 11/40 (28%) |
| spotlighting | 5/40 (12%) |
| stacked defenses, stamp forged | 4/40 (10%) |
| stacked + answer check, stamp forged | 2/40 (5%) |
| memory gate (hold) | 0/40 (0%) |

- Undefended adoption at most 40%: **missed (45%)**, though under the 49% falsifier and below the small-model mean of 49%.
- Gate at 0%: **held.** Utility at 90% or above: **held** (4 of 4 clean answers; a very small count).
- Quiet payloads adopted more than loud ones: **held** (75% against 12% undefended).
- **The larger model is not harder to fool undefended, but it follows the prompt-level defenses far better.** Spotlighting cut it
  from 45% to 12% (the small models: 49% to 34%), and the stacked defenses with a forged stamp to 10% (small models: 30%).
  The gate was still the only defense at 0 for every model.

**Run 2, Palimpsest judge benchmark, held-out 71 cases:**
- Alone: **58% (46% to 68%)**. The prediction (above 58%) **failed**: it ties the best small chat models, and the falsifier
  (58% or less) triggered. A larger model asked directly is no better at this task.
- As the hybrid's refiner: **76% (65% to 84%)**, inside the predicted 70 to 80% band, but it missed **33%** of true conflicts
  (the `qwen2.5:7b` refiner missed 8%). A more capable model gave the refiner more confidence to call a conflict an exception
  or a replacement. Not a recommended refiner.

Limits: one 8B model; 40 answers per cell; batch 4's errors had already been read, so Run 2 is not a fresh held-out test.
