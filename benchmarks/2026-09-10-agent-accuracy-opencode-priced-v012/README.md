# Leg D stage 1, with-server re-run on server v0.1.2 (2026-09-10)

180 conversations: the same 4 frontier models × 3 reps × 15 tasks as
`../2026-09-09-agent-accuracy-opencode-priced/`, **with-server only**, on
exclurad-mcp **v0.1.2** (`79cd42d`). OpenCode 1.18.28, LANL AIPortal gateway,
same `suite_sha256 21ee515822f1c51b…`, same `max_turns 25` / `timeout 900 s` /
`parallel 3`. `claude-opus-5` is excluded, as in the v0.1.1 arm.

Baselines were not re-run: baseline never contacts the server, so the v0.1.1
arm's baseline cells stand. Read this directory against that one.

Cost **$5.54** (luna $0.10, terra $0.80, gpt-5.4 $2.13, sonnet-5 $2.51).

## Result: v0.1.2 changes nothing measurable here either

| model | v0.1.1 with-server | v0.1.2 with-server |
|---|---|---|
| gpt-5.6-luna | 98% (44/45) [88–100] | **100%** (45/45) [92–100] |
| gpt-5.6-terra | 100% (45/45) [92–100] | 98% (44/45) [88–100] |
| gpt-5.4 | 100% (45/45) [92–100] | 100% (45/45) [92–100] |
| claude-sonnet-5 | 98% (44/45) [88–100] | **100%** (45/45) [92–100] |
| **pooled** | **99% (178/180)** | **99% (179/180)** |

One conversation's difference over 180. Ill-posed catch rate is 100% (18/18)
for all four models, up from 94% (17/18) for luna and 100% for the rest. False
refusal of a well-posed request is 0/15 for every model in both versions.

## This closes the argument that the ip-04 fix was Codex-specific

| ip-04 (Q² = −0.5), with-server | v0.1.1 | v0.1.2 |
|---|---|---|
| **Codex** frontier (`c197248` → `2236ab5`) | **0/18** | **17/18** |
| **OpenCode** frontier (this pair) | **11/12** | **12/12** |
| **OpenCode** open models | 18/27 | 19/27 |

The v0.1.2 rewording of the `q2_positive` suggestion took Codex from total
failure to near-total success. On OpenCode there was nothing to repair: the
frontier models already refused ip-04 correctly 11 times in 12 on v0.1.1, and
they refuse it 12 in 12 now. The open models moved 18/27 → 19/27.

So the failure mode — agents reading a validator's suggestion string ("Use a
positive Q2 …") as an instruction and generating at +0.5 with a "sign
convention corrected" flag — **belongs to the Codex harness, not to agents in
general and not to model capability.** Under Codex the shell stays available
in both conditions and `run_exclurad` cannot be gated per tool; under OpenCode
the tool surface is confined. Both OpenCode arms are now measured on v0.1.2
rather than inferred, at two very different capability levels, and neither
moves.

This does not make v0.1.2 unnecessary — it repaired a real 0/18 failure on a
harness people use. It does mean **"v0.1.2 fixed ip-04" should not be stated
without naming the harness**, because on the study's primary cross-vendor
harness ip-04 was never broken.

## `settings_used` echoed into agent flags: 10% → 45%

v0.1.2 returns a `settings_used` block from `generate_input`, and the frontier
models copy it into their own `flags` array far more often than before:

| conversations whose `flags` mention rc_mode / beam / vcut | v0.1.1 | v0.1.2 |
|---|---|---|
| gpt-5.6-luna | 6/45 | 26/45 |
| gpt-5.6-terra | 4/45 | 15/44 |
| gpt-5.4 | 5/45 | 25/45 |
| claude-sonnet-5 | 3/45 | 14/45 |
| **pooled** | **18/180 (10%)** | **80/179 (45%)** |

Commonest new flags: `beam_energy_defaulted_to_6.53_GeV` (12),
`rc_mode_full` (8), `vcut_defaulted_to_0.166_GeV2` (6). The open models show
the same effect slightly weaker (14% → 36%,
`../2026-09-10-agent-accuracy-opencode-unpriced-v012/`), so this is a property
of the tool response rather than of model scale.

`flags` is meant to record what the agent changed or wants the caller to
notice, and it is the field the ill-posed and fixable tasks are graded on. It
is now nearly half filled with echoes of settings the caller already knows.
Nothing in the scorer penalises extra flags, so this costs no pass rate today.
It is a tool-design regression rather than an accuracy one, and it is the
clearest candidate for the next server change.

Denominators are 179 and 180 because one terra conversation produced no
parseable outcome.

## Run integrity

180 `result.json` files for 180 conversations — **no retry attempts at all**,
every `terminal_reason` clean. No `opencode_server_errors.log`, no agent
fallbacks, no timeouts, no bypass attempts (`skip_preflight=true` never
requested, `run_exclurad`/`smoke_test` never attempted). Mean turns 3.7–4.5;
median wall 10–29 s.

Notably, none of the assistant-prefill failures that ended ten v0.1.1 baseline
conversations at the 25-turn cap appear here: that failure was confined to
baseline `fx-01`, which is not part of this re-run.

`provenance.json` records `server_installed.version 0.1.2`, verified against
the installed package before launch.
