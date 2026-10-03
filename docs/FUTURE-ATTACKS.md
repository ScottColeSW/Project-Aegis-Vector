# Attacks not yet tested

Recorded 2026-10-02 so they are not forgotten. The project's order is defenses first: each item below should get a defense
design, pre-registered, before its attack is run, so the attack measures something we tried to stop. The categories are from
the author's recollection of the poisoning and prompt-injection literature; check the specifics before citing any of it.

What the battery covers today: ten single-document forgeries (override, injected instruction, polite memo, borrowed real
number, no number, one-off exception, buried in a benign memo, query mirroring, and `inside_job`), and a compromised door that
forges the "verified" source stamp.

| Attack | Why it matters | What is already known here |
|---|---|---|
| **Many forged documents at once** | Several agreeing forgeries can out-vote the truth in retrieval, and in Palimpsest a later forgery could reinforce an earlier one if that one was ever admitted. | The gate holds each arrival, so one held document cannot be reinforced; not tested as a set. Closest to an obvious gap. |
| **Slow drift** | Many small changes, each below a figure check, add up to a different fact. | Figure checks are per arrival; nothing tracks cumulative change. |
| **Attacks on the write path** | The attacker steers what the agent itself decides to remember in conversation, with no document upload at all. | Palimpsest holds external claims for a person, but agent-originated claims were not attacked. |
| **Attacks on retrieval** | Text engineered to land near a query in embedding space, not written for a person to read. | Query mirroring is the mild version; nothing adversarial against the embedder. |
| **Facts without figures** | The rules lean on numbers; the NLI alternative was too noisy; the registry covers only registered facts. | A forged name, date or policy with no figure has the weakest protection. |
| **Poisoning the verified corpus** | If the trusted source is wrong, every defense downstream agrees with it. | Out of scope for a gate; needs provenance and review upstream. |
| **Other languages and encodings** | A payload the English rules and small models read differently. | Untested. |
| **Structured output and tool calls** | Agents mostly work in JSON or tool calls, not free-text answers; a defense measured only on free text may behave differently when the model fills a field. Raised by the project owner 2026-10-02. | Untested. Reasoning models such as `qwen3:4b` already work in JSON mode with no token cap (Evo uses them that way). A small first test: one model, one payload. |
| **Attacker model that writes the forgeries** | Every payload so far was written by hand, so "one adaptive payload" is not a sample of attacks. A model that adapts over turns (an attack/defend loop, as in a script from a Gemini suggestion, 2026-10-03) would test that limit. | Not built. Adapt the idea: the attacker writes forged documents aimed at getting the assistant to state the forged $100,000 limit; the existing judge labels the answers; compare the memory gate with the other defenses. Needs many runs per pairing (the sketch ran once, three turns, at temperature 0.8), a check for transformed leaks, a no-defense baseline, and the attacker's payload separated from its commentary. Borrow one idea from the judge node in the same suggestion: a categorical technique label per payload (roleplay, encoding, social engineering and so on), used as a tag after the fact so results can be reported by technique. Do not borrow its 1-to-10 attack and defense scores, which are unvalidated. A different, simpler attack (leaking a secret from a system prompt) is not what this project tests. Costly and GPU-heavy: ask before running. |
| **Registry authority** | Whoever can approve registrations decides what the gate protects; a forged figure registered as verified wins. | Stated as a limit in `PREREGISTRATION-proposed-registry.md`; not measured. |

Known defenses that failed or were not enough, so they are not retried blindly: the perplexity filter (threshold above every
payload), registry-free NLI comparison (14 of 21 false alarms), and an agent-proposed registry approved as proposed (7 of 10
payloads, 5 of 21 false alarms).
