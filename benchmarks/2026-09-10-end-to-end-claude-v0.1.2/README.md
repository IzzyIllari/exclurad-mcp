# Leg E with-server on server v0.1.2 — Claude Code (sonnet + haiku, k=3)

36 conversations, $2.19, 36/36. Haiku went 15/18 -> 18/18; sonnet was
already 18/18 and is unchanged.

Mechanism, counted from the transcripts rather than inferred. Beam energy
passed to `generate_input`, with-server conversations:

| version | haiku 10.6 GeV | haiku 6.53 GeV | haiku default | sonnet 10.6 |
|---|---|---|---|---|
| v0.1.1 | 3 | 8 | 7 | 0 |
| v0.1.2 | 0 | 7 | 11 | 0 |

v0.1.2 makes `generate_input` return `settings_used` and a note naming the
channel's campaign energies. Haiku stopped assuming 10.6 GeV (which is
correct physics for RG-A but not the RG-K reference these tasks come from);
sonnet's choices are identical across versions. The fix moved the weaker
model without disturbing the stronger one. The task wording was deliberately
NOT changed (PROTOCOL-E.md, "Known asymmetries").
