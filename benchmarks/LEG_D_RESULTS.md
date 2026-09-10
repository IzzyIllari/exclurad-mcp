# Leg D — index of arms and what each one establishes

Written 2026-09-10. This is the map of the agent-accuracy study: which
directories hold scored data, what question each answers, and what is still
open. Per-arm detail lives in each run directory's own `README.md`; this file
exists so nobody has to reverse-engineer the set from directory names.

**2,998 scored conversations across 24 run directories** (leg D and leg E
combined). Every arm below records its own `provenance.json` with
`server_installed.version`, `suite_sha256`, harness version and binary hash.
The task suite is identical everywhere: `suite_sha256 21ee515822f1c51b…`.

## The three claims the study supports

**1. The server's value is inversely proportional to model capability.**
Frontier models gain +16 to +18 points from the server. Open models gain up to
+60. This is the strongest result in the study and the one with an audience:
most people who would run this server do not have frontier API access.

| | with-server | baseline | gap |
|---|---|---|---|
| NVIDIA Nemotron 3 Super 120B | 100% (45/45) | 40% (18/45) | +60 |
| NVIDIA Nemotron 3 Nano 30B | 78% (35/45) | 31% (14/45) | +47 |
| gpt-oss-120b | 58% (26/45) | 27% (12/45) | +31 |
| Mistral Medium 3.5 128B | 89% (40/45) | 62% (28/45) | +27 |
| Laguna S 2.1 | 96% (43/45) | 76% (34/45) | +20 |
| Inkling Small | 100% (45/45) | 87% (39/45) | +13 |
| gemma-4-31B-it | 96% (43/45) | 84% (38/45) | +12 |
| Lightning 30B | 44% (20/45) | 33% (15/45) | +11 |
| Muse Glimmer 30B | 4% (2/45) | 4% (2/45) | 0 |
| *frontier, for comparison* | *98–100%* | *80–84%* | *+16 to +18* |

Source: `2026-09-09-agent-accuracy-opencode-unpriced/` (open, server v0.1.1)
and `2026-09-09-agent-accuracy-opencode-priced/` (frontier, v0.1.1).

**2. The v0.1.2 ip-04 fix was harness-specific.** Server v0.1.2 reworded the
`q2_positive` validator suggestion, which agents had been reading as an
instruction ("Use a positive Q2 …") and obeying — generating at +0.5 with a
"sign convention corrected" flag instead of refusing Q² = −0.5.

| ip-04, **with-server only** | v0.1.1 | v0.1.2 |
|---|---|---|
| Codex frontier | **0/9** | **8/9** |
| OpenCode frontier | 11/12 | 12/12 |
| OpenCode open models | 18/27 | 19/27 |

Codex goes from total failure to near-total success. Neither OpenCode arm
moves, because under OpenCode ip-04 was never broken. Under Codex the shell
stays available in both conditions and `run_exclurad` cannot be gated per
tool; under OpenCode the tool surface is confined.

**"v0.1.2 fixed ip-04" must name the harness.** On the study's primary
cross-vendor harness, there was nothing to fix.

> **Denominator warning.** `benchmarks/2026-09-10-agent-accuracy-codex-v0.1.2-with-server/README.md`
> states this as "0/18 → 17/18" with the denominator labelled "3 models × 3
> reps". 3 × 3 = 9, and that arm's own per-task table reads 3/3 + 2/3 + 3/3 =
> 8/9. Counting `scores.json` directly: Codex v0.1.1 ip-04 is 0/9 with-server
> **and** 0/9 baseline (which is where 18 comes from — it pools conditions),
> and Codex v0.1.2 with-server is 8/9. `17/18` does not appear in the data.
> The with-server-to-with-server comparison is **0/9 → 8/9**. That README has
> not been edited here; it is its author's to correct.

**3. `settings_used` is being echoed into agent `flags`.** v0.1.2's
`generate_input` returns a `settings_used` block, and agents copy it into their
own `flags` array:

| conversations whose `flags` mention rc_mode / beam / vcut | v0.1.1 | v0.1.2 |
|---|---|---|
| frontier (OpenCode) | 18/180 (10%) | 80/179 (**45%**) |
| open models (OpenCode) | 45/312 (14%) | 108/302 (**36%**) |

Every model went up, so this tracks the tool response rather than model scale.
Commonest new flags: `beam_energy_defaulted_to_6.53_GeV`, `rc_mode_full`,
`vcut_defaulted_to_0.166_GeV2`. `flags` is meant to say what the agent changed
or what the caller should notice, and it is the field the ill-posed and fixable
tasks are graded on; it is now nearly half echoes of settings the caller
supplied. **This costs no pass rate today** — the scorer does not penalise
extra flags — so it is a tool-design regression, not an accuracy one. It is the
clearest candidate for the next server change.

## Two findings about measurement, not about physics

**Delivery failures are a large fraction of some models' scores.** A
"chat-text outcome" is a conversation with no `outcome.json` the scorer can
find, whose final assistant message carries the outcome JSON anyway — the model
did the work and printed the answer instead of writing it.

Nemotron 3.5 Lightning 30B is the one model the server makes *worse* on the
scoreboard (25 unusable with-server against 11 baseline on v0.1.1). 24 of those
25 are chat-text. On v0.1.2 it is 32 of 32. Its ceiling, if those had been
written and passed, is 45/45. gpt-oss-120b does the same 11 times in each
condition, i.e. independent of the server.

Full per-model, per-condition counts are in
`2026-09-09-agent-accuracy-opencode-unpriced/README.md`.

**Muse Glimmer 30B's 4% is a serialization failure, not a physics failure.**
It passed the tool-surface probe on all seven axes with a profile identical to
Inkling Small's, which scores 100%. But 84 of its 90 cells fail JSON parsing
with plausible physics inside the file, in at least four flavours: Python
`dict` repr with single quotes (35 files), unexpanded `\u0022` escapes (7),
SSE `data: {"action":"refuse"}` framing, one file that is `eyJhIjoiYiJ9`
(base64 of `{"a":"b"}`), and one truncated to the 9 bytes `{"action"`. 42 of
the 84 repair mechanically into a dict carrying an `action`; the repaired
payloads were **not** scored, so no pass rate is claimed for them.

The probe finding survives in a sharper form: **a tool-surface probe proves the
harness is wired correctly and proves nothing about whether a model can emit a
file.**

## Arm index

Scored arms only; shakedowns and discarded pilots are omitted (each carries a
README saying it feeds no table).

| directory | harness | server | models × conds × k | conv | what it is for |
|---|---|---|---|---|---|
| `2026-09-09-agent-accuracy-opencode-priced` | OpenCode | 0.1.1 | 4 × 2 × 3 | 360 | frontier baseline for the whole study |
| `2026-09-09-agent-accuracy-opencode-unpriced` | OpenCode | 0.1.1 | 9 × 2 × 3 | 810 | the open-model result (claim 1) |
| `2026-09-10-agent-accuracy-opencode-priced-v012` | OpenCode | 0.1.2 | 4 × 1 × 3 | 180 | frontier, v0.1.2 (claim 2) |
| `2026-09-10-agent-accuracy-opencode-unpriced-v012` | OpenCode | 0.1.2 | 9 × 1 × 3 | 405 | open models, v0.1.2 (claim 2) |
| `2026-09-09-agent-accuracy-codex` | Codex | 0.1.1 | 3 × 2 × 3 | 270 | Codex arm, labelled replication |
| `2026-09-10-agent-accuracy-codex-v0.1.2-with-server` | Codex | 0.1.2 | 3 × 1 × 3 | 135 | Codex on v0.1.2 |
| `2026-09-09-agent-accuracy-codex-terra-replication-laptop` | Codex | 0.1.1 | 1 × 2 × 3 | 90 | cross-machine replication of terra |
| `2026-09-09-agent-accuracy-claude-v0.1.1-with-server` | Claude Code | 0.1.1 | 2 × 1 × 3 | 90 | Claude Code arm |
| `2026-09-10-agent-accuracy-claude-v0.1.2-with-server` | Claude Code | 0.1.2 | 2 × 1 × 3 | 90 | Claude Code on v0.1.2 |
| `2026-09-08-agent-accuracy` | Claude Code | — | 2 × 2 × 3 | 180 | first run; predates provenance hardening |
| *leg E (`2026-09-10-end-to-end-*`)* | mixed | 0.1.1 / 0.1.2 | — | 270 | end-to-end suite, separate protocol |

**Baselines are never re-run across server versions.** Baseline conversations
have no MCP server, so a v0.1.1 baseline cell is valid against a v0.1.2
with-server cell. Every `-v012` directory is with-server only, by design.

**Codex rows are a labelled replication and are never pooled** with OpenCode or
Claude Code rows: per `agent_tasks/PROTOCOL.md`, the Codex shell stays
available in both conditions and `run_exclurad` cannot be removed per tool.

## Provenance and integrity notes

- `terminal_reason` labels why a conversation stopped when something external
  stopped it. Signatures: `assistant_prefill_rejected`, `opencode_db_locked`,
  `context_window_exceeded`, `content_filter_blocked`, `wall_clock_timeout`,
  and `provider_quota_exhausted`.
- **`provider_quota_exhausted` was added 2026-09-10** after a ChatGPT
  subscription limit killed 121 of 270 conversations in a Codex run. A quota
  kill ends a conversation in ~2 s with `num_turns=1` and no output, so an
  affected cell scores 0 **while looking like a fast, confident model
  failure**. All 121 were originally labelled `null`. Any arm run on a
  subscription-metered harness should be checked for this before it is
  believed.
- The `sol` and `luna` cells of the laptop Codex run were deleted rather than
  reported for exactly that reason (45–100% quota-killed). Clean cells for both
  already exist in `2026-09-09-agent-accuracy-codex`.
- `report_leg_d_combined.chat_text_outcome()` uses a shallow
  `(dir/"outcome.json").exists()` check, but the scorer's `find_outcome()` also
  accepts the file one level down — baseline agents sometimes write it inside
  the source tree they read. The shallow check reports 20 missing for
  gpt-oss-120b baseline where the scorer sees 18, 9 for Laguna where it sees 2,
  3 for Mistral where it sees 1. **In the committed datasets this changes no
  chat-text count**, so every published number is unaffected; the counts in the
  run READMEs were computed with `find_outcome()`. The discrepancy is latent,
  not active, and should be fixed before the shallow check is trusted on a new
  run.
- The runner's `--server-bin` default points at a repo-root path that does not
  exist. If it is not passed explicitly, `provenance.server_installed` silently
  records `null`. Every scored arm passes it explicitly.

## Open, as of 2026-09-10

1. **The ablation.** Not specified yet — what is removed (individual server
   tools? the suggestion strings inside validator FAILs? the `notes` block?),
   on which models, with-server only? Given claim 2, the sharpest version is
   stripping the suggestion strings and testing ip-04-style compliance **on
   Codex specifically**, since that is the only harness where the strings
   demonstrably drive behaviour.
2. **The `flags` dilution** (claim 3) — a `server.py` change, not made here.
3. **The combined multi-harness report** — in progress separately. When it
   pools arms, the denominator warning above and the "Codex is never pooled"
   rule both apply.
4. **Dropped deliberately:** the gpt-oss-20b append (least valuable remaining),
   and re-running the quota-killed sol/luna cells.
