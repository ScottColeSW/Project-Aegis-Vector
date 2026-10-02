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
| **Registry authority** | Whoever can approve registrations decides what the gate protects; a forged figure registered as verified wins. | Stated as a limit in `PREREGISTRATION-proposed-registry.md`; not measured. |

Known defenses that failed or were not enough, so they are not retried blindly: the perplexity filter (threshold above every
payload), registry-free NLI comparison (14 of 21 false alarms), and an agent-proposed registry approved as proposed (7 of 10
payloads, 5 of 21 false alarms).
