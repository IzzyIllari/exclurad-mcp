# Leg D with-server on server v0.1.2 — Codex (sol / terra / luna, k=3)

135 conversations, tokens only. sol 45/45, terra 44/45, luna 44/45.

The headline is ip-04 (Q2 = -0.5 GeV2), the task the v0.1.2 wording change
targeted:

| | v0.1.1 | v0.1.2 |
|---|---|---|
| ip-04, with-server, 3 models x 3 reps | 0/18 | 17/18 |

On v0.1.1 every conversation read the suggestion "Use a positive Q2 ..." as
an instruction, flipped the sign, and generated at +0.5. On v0.1.2 the same
models, same prompts, refuse and state the convention problem. The single
remaining miss (terra rep2) still flips the sign, but its explanation now
names the convention explicitly rather than treating it as a routine fix.

Also visible in the outcomes: agents now echo the settings the server
reported, e.g. flags `beam_energy_defaulted_to_6.53_GeV` and
`full_o_alpha_rc`, which no v0.1.1 conversation ever mentioned.

The other miss is luna rep1 fx-04, an outcome.json truncated mid-string
(model formatting, not physics; the same class of defect as the 2026-09-09
luna ip-06 missing brace).
