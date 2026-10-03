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
