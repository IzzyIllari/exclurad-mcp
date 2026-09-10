# Leg D stage 2, with-server re-run on server v0.1.2 (2026-09-10)

405 conversations: the same 9 open models × 3 reps × 15 tasks as
`../2026-09-09-agent-accuracy-opencode-unpriced/`, **with-server only**, on
exclurad-mcp **v0.1.2** (`79cd42d`, "stop the tool interface deciding the
physics"). OpenCode 1.18.28, same gateways, same `suite_sha256
21ee515822f1c51b…`, same `max_turns 25` / `timeout 900 s` / `parallel 3`.

The 405 **baseline** conversations were not re-run and are not duplicated
here: baseline never contacts the server, so the v0.1.1 arm's baseline cells
remain valid as they stand. Read this directory against that one.

## Headline: v0.1.2 changed almost nothing for these models

| model | v0.1.1 with-server | v0.1.2 with-server | Δ |
|---|---|---|---|
| NVIDIA Nemotron 3 Nano 30B | 78% (35/45) | 89% (40/45) | **+11** |
| gemma-4-31B-it | 96% (43/45) | 98% (44/45) | +2 |
| gpt-oss-120b | 58% (26/45) | 56% (25/45) | −2 |
| Mistral Medium 3.5 128B | 89% (40/45) | 87% (39/45) | −2 |
| Inkling Small | 100% (45/45) | 98% (44/45) | −2 |
| NVIDIA Nemotron 3 Super 120B | 100% (45/45) | 96% (43/45) | −4 |
| Laguna S 2.1 | 96% (43/45) | 91% (41/45) | −5 |
| Muse Glimmer 30B | 4% (2/45) | 2% (1/45) | −2 |
| NVIDIA Nemotron 3.5 Lightning 30B | 44% (20/45) | 29% (13/45) | **−15** |
| **pooled** | **74% (299/405)** | **72% (290/405)** | −2 |

Every Δ except Nano's and Lightning's is within one or two conversations, i.e.
run-to-run noise at k=3. Excluding Lightning the pooled figures are 77.5% and
76.9% — flat.

## Why: the ip-04 trap was harness-specific, and OpenCode never had it

The rerun was motivated by ip-04 (Q² = −0.5) going **0/18 → 17/18** on the
Codex frontier models when the `q2_positive` suggestion string was reworded.
That gain does not reproduce here, because under OpenCode there was nothing to
gain — ip-04 already worked on v0.1.1:

| ip-04, with-server | v0.1.1 | v0.1.2 |
|---|---|---|
| NVIDIA Nemotron 3 Nano 30B | 1/3 | **3/3** |
| Laguna S 2.1 | 2/3 | **3/3** |
| gpt-oss-120b | 1/3 | 1/3 |
| NVIDIA Nemotron 3 Super 120B | 3/3 | 3/3 |
| gemma-4-31B-it | 3/3 | 3/3 |
| Mistral Medium 3.5 128B | 3/3 | 3/3 |
| Inkling Small | 3/3 | 3/3 |
| Muse Glimmer 30B | 0/3 | 0/3 |
| NVIDIA Nemotron 3.5 Lightning 30B | 2/3 | **0/3** |
| **total** | **18/27** | **19/27** |

For context on the same task and the same server v0.1.1: the **Codex** frontier
models scored **0/18**, while the **OpenCode** frontier models scored **11/12**
(`../2026-09-09-agent-accuracy-opencode-priced/`), and these open models under
OpenCode scored 18/27.

So the failure the v0.1.2 wording fix repaired was **an interaction between the
suggestion string and the Codex harness, not a property of the string alone.**
Under Codex the shell stays available in both conditions and `run_exclurad`
cannot be gated per tool; under OpenCode the tool surface is confined. Whatever
drove Codex's agents to read "Use a positive Q2 …" as an instruction did not
drive OpenCode's, at any model scale.

**This means the question the rerun was meant to answer cannot be answered from
ip-04.** "Does better tool wording help a weak model more or less than a strong
one" needs a task where the weak models actually failed on v0.1.1 for wording
reasons; ip-04 is not that task on this harness. The one real movement, Nano's
1/3 → 3/3, is a single model over three conversations.

## Lightning 30B's −15 is entirely a delivery failure

| Lightning 30B, with-server | v0.1.1 | v0.1.2 |
|---|---|---|
| scored passes | 20/45 (44%) | 13/45 (29%) |
| outcomes the scorer could not find | 25 | 32 |
| of those, emitted as chat text | 24 | **32 (all of them)** |
| ceiling if chat-text outcomes had been written *and* passed | 44/45 (98%) | 45/45 (100%) |

Every one of its 32 unusable conversations on v0.1.2 is the model calling the
MCP tools correctly, writing the input file, then printing the outcome JSON in
its reply instead of writing it to disk. Its scoreboard drop is not a physics
regression, and the ceiling row moves the *other* way. Lightning's number
should not be read as a v0.1.2 effect.

Chat-text counts for the other models are unchanged from v0.1.1: gpt-oss-120b
11 (of 19 missing), Nano 1 (of 4), everything else 0. Counted with the
scorer's `find_outcome()`, which also accepts an `outcome.json` one level down.

## `settings_used` does get echoed into agent flags, and not only by frontier models

v0.1.2 returns a `settings_used` block from `generate_input`. The frontier
models began copying it into their own `flags` array; the open models do the
same, at more than double the previous rate:

| conversations whose `flags` mention rc_mode / beam / vcut | v0.1.1 | v0.1.2 |
|---|---|---|
| pooled | 45/312 (14%) | 108/302 (**36%**) |

Every model with parseable outcomes increased. Largest movers: Laguna S
8/45 → 26/45, Nemotron 3 Nano 2/41 → 14/40, gemma-4-31B 6/45 → 15/45. The most
common new flag is `rc_mode=full` (7 of 9 models), then `beam_gev=6.53` and
`vcut=0.166`.

These are settings, not deviations, so the `flags` field is drifting from
"things the caller should know changed" toward "an echo of the call". Nothing
in the scorer penalises extra flags, so this costs no pass rate today, but it
dilutes the field that the ill-posed and fixable tasks are graded on and is
worth watching. Denominators differ (312 vs 302) because unparseable and
missing outcomes are excluded.

## Run integrity

409 `result.json` files: 405 scored conversations, all `terminal_reason`
clean, plus 4 retry attempts labelled `opencode_db_locked`. No
`opencode_server_errors.log`, no agent fallbacks, no timeouts, no bypass
attempts. The db-locks are SQLite contention on OpenCode's shared session DB
when the three workers start together; all recovered on retry. Cost $0.00 —
every model here is free on the LANL gateways. Wall time ~2 h 10 m.

`provenance.json` records `server_installed.version 0.1.2`, confirmed against
the installed package before launch.
