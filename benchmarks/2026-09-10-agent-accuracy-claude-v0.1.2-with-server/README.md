# Leg D with-server on server v0.1.2 — Claude Code (sonnet + haiku, k=3)

90 conversations, $3.11. Both models 45/45, every task class perfect.

Before/after on the three tasks the validator wording used to decide
(with-server only; baseline never touches the server):

| task | v0.1.0 | v0.1.1 | v0.1.2 |
|---|---|---|---|
| fx-01 (clamp ±1) | 6/6 | 6/6 | 6/6 |
| ip-06 (\|cos\|>1) | 1/6 | 6/6 | 6/6 |
| ip-02 (W below threshold) | 4/6 | 6/6 | 6/6 |
| ip-04 (Q2 < 0) | 6/6 | 6/6 | 6/6 |

The Claude models mostly refused ip-04 already; the Codex arm is where the
Q2 suggestion string was doing damage (see the sibling codex run dir).
