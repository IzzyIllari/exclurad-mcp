# Leg E with-server on server v0.1.2 — Codex (sol / terra / luna, k=3)

54 conversations, 54/54. luna went 13/18 -> 18/18; sol and terra were
already 18/18 and 18/18.

Mechanism, counted from the transcripts. `rc_mode` passed to
`generate_input`, with-server conversations:

| version | luna leading-log | luna full | sol leading-log | omitted |
|---|---|---|---|---|
| v0.1.1 | 11 | 3 (after retry) | 1 | 42 |
| v0.1.2 | 0 | 45 | 0 | 9 |

On v0.1.1 `rc_mode` was 0/1 and read like a boolean; luna passed 1 (the
factorized leading-log APPROXIMATION) in 11 of its 15 computable
conversations while being asked for an exact correction. v0.1.2 takes
"full"/"leading_log" and states which was used: every model now names
"full" explicitly in 15 of 18 conversations and omits it (taking the
documented default) in the rest. Nobody asked for the approximation.

Measured cost of that substitution on the eta reference point: delta
0.8493 (leading-log) against 0.9160 (full), a 7% error, plus zero
radiative correction to the beam-spin asymmetry. On v0.1.1 the runner's
NO_TAI misclassification accidentally prevented luna reporting the
approximate number as exact; v0.1.2 fixes both, so the guard is now the
parameter name rather than a bug.
