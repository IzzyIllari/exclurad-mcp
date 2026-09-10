# Leg D stage 2 — OpenCode open-model arm (2026-09-09), server v0.1.1

810 conversations: 9 models × 2 conditions × 3 reps × 15 tasks. OpenCode
1.18.28, exclurad-mcp **v0.1.1**, LANL AIPortal and Darwin gateways. No model
here is a frontier closed model; all nine are open-weight or lab-hosted, which
is the point of the arm — most people who would run this server do not have
frontier API access.

Full tables in `tables.md`; per-conversation rows in `results.csv`.

## The result: the server helps weak models far more than strong ones

| model | with-server | baseline | gap |
|---|---|---|---|
| NVIDIA Nemotron 3 Super 120B | **100%** (45/45) [92–100] | 40% (18/45) [27–55] | **+60** |
| NVIDIA Nemotron 3 Nano 30B | 78% (35/45) [64–87] | 31% (14/45) [20–46] | **+47** |
| gpt-oss-120b | 58% (26/45) [43–71] | 27% (12/45) [16–41] | +31 |
| Mistral Medium 3.5 128B | 89% (40/45) [77–95] | 62% (28/45) [48–75] | +27 |
| Laguna S 2.1 | 96% (43/45) [85–99] | 76% (34/45) [61–86] | +20 |
| Inkling Small | **100%** (45/45) [92–100] | 87% (39/45) [74–94] | +13 |
| gemma-4-31B-it | 96% (43/45) [85–99] | 84% (38/45) [71–92] | +12 |
| NVIDIA Nemotron 3.5 Lightning 30B | 44% (20/45) [31–59] | 33% (15/45) [21–48] | +11 |
| Muse Glimmer 30B | 4% (2/45) [1–15] | 4% (2/45) [1–15] | 0 |

The four frontier models in the priced arm
(`../2026-09-09-agent-accuracy-opencode-priced/`) gained **+16 to +18** points
on the same suite, same harness, same server version. The open models here gain
up to **+60**. Nemotron 3 Super 120B goes from 40% to a perfect 45/45.

Read the other way: with the server, five of the nine open models land at
89–100%, which is the band the frontier models occupy in both conditions. The
server does not raise the ceiling; it lets weaker models reach it.

## Safety axes

False refusal of a well-posed request is **0/15 for all nine models in the
with-server condition**. In baseline, three models refuse feasible work:
Nemotron 3 Nano 20% (3/15), Nemotron 3 Super 7% (1/15), Laguna S 7% (1/15).

Ill-posed catch rate moves the most:

| model | with-server | baseline |
|---|---|---|
| Nemotron 3 Super 120B | 100% (18/18) | 44% (8/18) |
| Mistral Medium 128B | 94% (17/18) | 39% (7/18) |
| Nemotron 3 Nano 30B | 89% (16/18) | 28% (5/18) |
| gpt-oss-120b | 50% (9/18) | 17% (3/18) |
| gemma-4-31B-it | 100% (18/18) | 100% (18/18) |
| Lightning 30B | 17% (3/18) | 39% (7/18) |

Lightning is the only model whose ill-posed catch rate goes **down** with the
server. See below — it is a delivery failure, not a judgement failure.

## Outcomes emitted as chat text, per model and condition

The Lightning finding rests on these counts, so they are given in full. A
"chat-text outcome" is a conversation with no `outcome.json` the scorer can
find, whose final assistant message nevertheless carries the outcome JSON —
the model did the work and printed the answer instead of writing it.

| model | with-server missing / of which chat text | baseline missing / of which chat text |
|---|---|---|
| gpt-oss-120b | 18 / **11** | 18 / **11** |
| Lightning 30B | 25 / **24** | 11 / **10** |
| Nemotron 3 Nano 30B | 4 / 1 | 6 / 0 |
| Nemotron 3 Super 120B | 0 / 0 | 2 / 0 |
| gemma-4-31B-it | 0 / 0 | 0 / 0 |
| Mistral Medium 128B | 0 / 0 | 1 / 0 |
| Laguna S 2.1 | 0 / 0 | 2 / 0 |
| Inkling Small | 0 / 0 | 0 / 0 |
| Muse Glimmer 30B | 0 / 0 | 1 / 1 |
| **total** | **47 / 36** | **41 / 22** |

Counted with the scorer's own `find_outcome()`, which also accepts an
`outcome.json` one level down (baseline agents sometimes write it inside the
source tree they read). A shallow `(dir/"outcome.json").exists()` check —
which is what `report_leg_d_combined.chat_text_outcome()` uses — reports 20
missing for gpt-oss-120b baseline, 9 for Laguna baseline and 3 for Mistral
baseline, because it misses the nested files. In this dataset that difference
changes no chat-text count, so the two methods agree on every number above;
the discrepancy is latent, not active, but it is real and worth fixing before
the shallow check is trusted on another run.

**Lightning 30B.** With the server it produces 25 unusable outcomes against 11
in baseline: the server made it *worse* on the scoreboard. But 24 of those 25
are chat-text — the model calls the MCP tools correctly, generates the input
file, and then emits the outcome JSON as markdown in its reply instead of
writing it. Its physics work is largely intact; its delivery is not.

**gpt-oss-120b.** 11 chat-text failures in each condition — identical, and so
independent of whether the server is present. That is a property of the model's
output habits, not of the tool surface.

**Sensitivity ceiling.** If every chat-text outcome had been written to disk
*and* scored a pass, Lightning would read 44/45 (98%) with-server against
25/45 (56%) baseline, and gpt-oss-120b 37/45 (82%) against 23/45 (51%). That
is an upper bound and is not a result: the payloads were not scored. It is
given only to show how much of these two models' scores is delivery rather
than physics.

## Muse Glimmer 30B: 4% is a serialization failure, not a physics failure

Muse Glimmer scores 4% in both conditions, and it **passed the tool-surface
probe on all seven axes** (`tool_surface.csv`) with a profile identical to
Inkling Small's — which scores 100%. So the probe proves the harness is wired
correctly; it proves nothing about whether a model can do the work.

But the 4% is not "cannot do the tasks". 84 of its 90 scored cells fail on
`outcome.json is not valid JSON`, and the file is almost always there with
plausible physics inside it. It fails to serialize, in at least four distinct
ways:

- **Python `dict` repr** (35 files): `{'action': 'generate_with_warning', ...}`
  — single quotes. One of these correctly identifies the `edge_cos_boundary`
  flag and states the |cos| ≤ 0.999 convention.
- **Unexpanded unicode escapes** (7 files): the six literal characters
  `\u0022` everywhere a `"` belongs, e.g.
  `{\u0022action\u0022:\u0022generate\u0022,…}`.
- **SSE framing**: `data: {"action":"refuse"}` — a correct refusal wrapped in
  a stream frame.
- **base64**: one file is `eyJhIjoiYiJ9`, which decodes to `{"a":"b"}`.
- **Truncation**: one file is the 9 bytes `{"action"`.

42 of the 84 repair mechanically into a dict carrying an `action`. Whether the
repaired payloads would have passed was not scored, so no pass rate is claimed
for them. The honest statement is that Muse Glimmer's score measures its JSON
emission and says almost nothing about its physics.

## Run integrity

821 `result.json` files (810 scored conversations + 11 retry attempts).
Terminal reasons: 817 clean, **3 `opencode_db_locked`**, **1
`wall_clock_timeout`** (Mistral Medium baseline). No
`opencode_server_errors.log`, no silent agent fallbacks, no bypass attempts —
`skip_preflight=true` was never requested and `run_exclurad`/`smoke_test` were
never attempted in any of the 405 with-server conversations. The db-locks are
SQLite contention on OpenCode's shared session DB at worker start; all three
succeeded on retry and none scored a cell.

Cost is $0.00: every model here is free on the LANL gateways. Median wall 18 s
with-server against 47 s baseline — the server also makes these models roughly
2.5× faster, because baseline spends its turns grepping the Fortran source for
the input-format conventions. Mean turns fall correspondingly (e.g. Nemotron 3
Super: 5.3 with-server, 15.6 baseline).

## Scope and provenance

`provenance.json`: `harness_version 1.18.28`, `server_installed.version
0.1.1`, `suite_sha256 21ee515822f1c51b…` (identical to the priced arm and the
Codex arms), `max_turns 25`, `timeout 900 s`, `parallel 3`, `max_attempts 3`.

`opencode.json` in every conversation carries a `MODEL_LIMITS` provider block
setting token ceilings for `meta.llama3-8b`, `meta.llama3-70b`,
`amazon.nova-pro`, `mistral7b` and `Mistral-Large-3-675B`. None of those five
appears in this arm, so the block is inert here; it is emitted unconditionally
so the recorded config does not depend on which model the run used.

**This arm ran entirely on server v0.1.1.** v0.1.2 (`79cd42d`) changed the
validator suggestion strings that the ill-posed tasks turn on — on the Codex
frontier models it moved `ip-04` from 0/18 to 17/18. The with-server cells are
therefore re-run on v0.1.2 in a separate dated directory. The 405 **baseline**
conversations here never contact the server and remain valid as they stand.
