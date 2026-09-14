# Legs D and E, combined report (2026-09-14)

The cross-harness, cross-model summary of the agent-accuracy study (leg D) and
the end-to-end study (leg E) of [docs/benchmark-plan.md](../../docs/benchmark-plan.md).
Every number here is regenerated from the per-conversation directories by
`report_leg_d_combined.py`, `report_leg_e.py` and `figure_gain_vs_baseline.py`;
nothing is typed in by hand. The arm-by-arm map, with each arm's caveats, is
[LEG_D_RESULTS.md](../LEG_D_RESULTS.md). Per `agent_tasks/PROTOCOL.md`, every
ratio states its condition and its denominator, and Codex rows are never pooled
with the other harnesses (the Codex shell stays available in both conditions).

```
leg_d/tables.md                    headline, pooled, by class, harness effect, before/after,
                                   per-quirk, cost and tokens, failure taxonomy
leg_d/figure_gain_vs_baseline.*    THE SLIDE FIGURE: gain vs baseline pass rate, one point per cell
                                   (*_slide.pdf: half-slide size, larger type; figure_gain_vs_baseline.py)
leg_d/figure_pooled_bars.*         pooled pass rate by scope, both conditions, Wilson CIs
                                   (*_slide.pdf: compact 4-scope variant; figure_slides.py)
leg_d/figure_combined.*            backup: every cell, both conditions, Wilson 95% CIs
leg_e/figure_leg_e.*               per model: baseline, with-server v0.1.1 → v0.1.2 (figure_slides.py)
leg_d/combined_results.csv         2,520 rows, one per conversation
leg_d/combined_summary.csv         one row per harness × model × server × condition
leg_d/taxonomy.csv                 failure modes, headline cells
leg_e/tables.md, lege_*.csv        leg E per cell, pooled, taxonomy, every failure
```

Inputs: nine leg D run directories (listed at the top of `leg_d/tables.md`) and
the four leg E directories `2026-09-10-end-to-end-{claude,codex}{,-v0.1.2}`. The
terra laptop replication (`2026-09-09-agent-accuracy-codex-terra-replication-laptop`)
is deliberately not an input: it re-runs an existing cell on a second machine
and account, and its job is to say whether that cell holds (it does, 13 of 15
tasks reproduce exactly in both conditions), not to add weight to it.

## For the DNP slide

**The sentence the data support.** Giving the agent a package of documented,
unit-tested checks and input-generation tools raised its pass rate on the same
15 tasks in every harness tested: on OpenCode, the primary cross-vendor
comparison, from 59% to 80% over 13 models; on Claude Code from 84% to 100%
over two; on Codex, a labelled replication that keeps its shell, from 84% to
99% over three. No well-posed request was falsely refused with the server.
The largest gains were for two open-weight models with low baseline scores
(+56 and +58 points); frontier models gained +11 to +20.

Harness rows are never pooled (PROTOCOL.md). An earlier version of this file
led with an all-18-cell pool, 85% (692/810) vs 66% (538/810); the arithmetic
is right but the pool mixes Codex, which has a different tool surface, with
the other two harnesses, so it is withdrawn as a headline.

**The convergence claim, as measured.** With the server, the six frontier
cells (OpenCode and Claude Code) span 98–100% (269/270 together, 99.6%);
without it they span 80–89%.
The nine open-weight models span 56–98% with the server against 27–87%
without, once the two models whose scores are delivery failures are set aside
(below). Correctness moved into the tooling, and the spread between models
narrowed with it; it did not vanish for the open models.

**The sentence that belongs on the same slide.** The layer carries its errors
to every model too. Three times in this study a sentence inside a tool result
decided what the agents did: the v0.1.0 clamp suggestion on |cos θ*| > 1 (both
Claude models obeyed it in 5 of 6 conversations), the v0.1.1 "use a positive
Q²" suggestion (Codex 0/9 → 8/9 on ip-04 after rewording, OpenCode unmoved),
and in leg E the boolean-looking `rc_mode=0/1` (luna chose the leading-log
approximation in 11 of 15 conversations; 0 after it became `"full"`). Fix once,
fixed everywhere; wrong once, wrong everywhere.

**Headline numbers** (15 tasks × k = 3 per cell, Wilson 95% intervals; the
full 18-cell table is `leg_d/tables.md`):

| | with the server | without | gain |
|---|---|---|---|
| **OpenCode, 13 models (primary)** | **80% (469/585) [77–83]** | **59% (348/585) [55–63]** | **+21 pp** |
| OpenCode frontier, 4 models | 99% (179/180) [97–100] | 82% (148/180) [76–87] | +17 pp |
| OpenCode open-weight, 9 models | 72% (290/405) [67–76] | 49% (200/405) [45–54] | +22 pp |
| OpenCode open-weight without the two delivery-broken models, 7 (sensitivity) | 88% (276/315) [84–91] | 58% (183/315) [53–63] | +29 pp |
| Claude Code, 2 models | 100% (90/90) [96–100] | 84% (76/90) [76–91] | +16 pp |
| Codex, gpt-5.6 sol / terra / luna (labelled replication, shell kept) | 99% (133/135) [95–100] | 84% (114/135) [77–90] | +14 pp |
| well-posed requests falsely refused, OpenCode / Claude Code / Codex | **0/195 / 0/30 / 0/45** | 5/195 / 0/30 / 0/45 | |
| ill-posed requests refused with the reason, OpenCode / Claude Code / Codex | 183/234 / 36/36 / 53/54 | 143/234 / 35/36 / 45/54 | |
| fixable class, OpenCode / Claude Code | 82% (127/156) / 100% (24/24) | 47% (75/156) / 58% (14/24) | |
| `skip_preflight` override used, OpenCode / Claude Code / Codex (with-server conversations) | 12/585 / 1/90 / 0/135 | n/a | |
| `run_exclurad` or `smoke_test` attempted where withheld | 0/810 | n/a | |
| cost per correct result, priced non-Codex cells (270 conversations each) | $0.032 | $0.147 | 4.6× |
| median wall time, OpenCode / Claude Code / Codex | 17 s / 20 s / 56 s | 46 s / 50 s / 54 s | |

The override count was reported as 1/810 until 2026-09-14. The scanner in
`report_leg_d.py` parsed only Claude Code's event format, so OpenCode and
Codex conversations were zero by construction; an external review of the raw
transcripts found the 12 OpenCode uses, and the scanner now reads all three
formats (PROTOCOL.md, amendment of 2026-09-14). All 13 uses completed a
`generate_input` call with `skip_preflight=true`; in most the agent had
already run `preflight_check` and repaired the point. The override is
available to any agent, not gated to an expert role.

Largest single-model gains: Nemotron 3 Nano 30B 31% → 89% (14/45 → 40/45),
Nemotron 3 Super 120B 40% → 96% (18/45 → 43/45), gpt-oss-120b 27% → 56%.
Two open-weight models moved the other way (Lightning −4, Muse Glimmer −2);
both are delivery failures, below. The gain-vs-baseline figure has the
baseline on both axes, so a descending trend is partly arithmetic (the
maximum gain is 100 − baseline); it shows where the large gains were, not an
inverse law between capability and benefit.

**Leg E, the agent actually runs the code** (6 η tasks × k = 3; references
are recorded October-2025 campaign rows; full table `leg_e/tables.md`):

| | with the server | without |
|---|---|---|
| server v0.1.2, five models (sonnet, haiku, sol, terra, luna) | **89/90** (60/60 well-posed, 15/15 threshold trap, 14/15 NaN trap) | (baseline not re-run) |
| server v0.1.1, same five models | 82/90 | 84/90 |
| NaN trap reported as NaN, all versions pooled | 28/30 | 14/15 |
| below-threshold trap refused | 30/30 | 15/15 |

The v0.1.2 total was published as 90/90 on 2026-09-10. An external review
on 2026-09-14 found that one scored NaN-trap pass (Codex, gpt-5.6-terra,
rep 1, e2e-05) never ran EXCLURAD: the agent overrode `work_dir`, got
"executable not found", and reported `failed` with δ null; the scorer's NaN
branch accepted "no valid delta" as a NaN observation. The scorer now requires
execution evidence for that task (PROTOCOL-E.md, amendment of 2026-09-14),
all four arms were rescored symmetrically, and exactly that one conversation
changed. The safer main-slide number is the well-posed computations, 60/60
(24/24 Claude Code, 36/36 Codex), with the traps stated separately.

These are the same six tasks that exposed the two v0.1.1 defects and then
evaluated the fixes; there is no held-out suite. Report the before/after as a
development-suite rerun, not as a generalisation test.

Every v0.1.1 with-server failure was an interface defect and was measured to
vanish on v0.1.2: Haiku assumed a 10.6 GeV beam in 3 conversations (0 once
`generate_input` echoed its settings and named the campaign energies); luna
passed `rc_mode=1` in 11 of 15 (0 once the parameter took `"full"` /
`"leading_log"`). The substitution it stopped is a 7% error in δ on the
reference point (0.8493 vs 0.9160) and removes the radiative correction to the
beam-spin asymmetry entirely. Baseline agents that succeed do so at 3–4× the
cost and 2–5× the wall time (sonnet: $0.35 and 251 s per conversation against
$0.09 and 79 s); their failures are reading σ_Born from the wrong `radtot`
column or rounding the reported number.

**Figures.** `leg_d/figure_gain_vs_baseline.pdf` (slide: one point per cell,
gain against baseline pass rate; Okabe–Ito orange = open-weight, blue =
frontier; hollow diamonds = Codex; grey crosses = the two delivery-broken
models). `leg_d/figure_combined.png` (backup: every cell, both conditions,
intervals).

**Transcript material for a still-frame "request → tool call → result →
decision" slide:**

1. With the server, negative Q² refused (Claude Code, Haiku 4.5, v0.1.2,
   4 turns, 18 s):
   `../2026-09-10-agent-accuracy-claude-v0.1.2-with-server/excerpts/claude-haiku-4-5-20251001__with-server__rep1__ip-04.md`
   — `list_channels`, then `preflight_check` returns `q2_positive FAIL` with
   the v0.1.2 suggestion "Do not reinterpret the sign on the user's behalf",
   and the agent refuses and asks which convention was meant.
2. Without the server, the same request "corrected" and generated (OpenCode,
   gpt-5.6-terra, baseline, rep 1):
   `../2026-09-09-agent-accuracy-opencode-priced/aiportal/aws-gov.gpt-5.6-terra/baseline/rep1/ip-04/outcome.json`
   — `fix_and_generate`, flag `q2_sign_convention_corrected`, "the requested
   q² = −0.5 GeV² was converted to input Q² = 0.5 GeV²". Of the 54 baseline
   ip-04 conversations in the headline cells, 20 chose `fix_and_generate`
   and 4 more generated anyway (24 proceeded); 21 refused; 9 delivered no
   parseable outcome. With the server: 45 refused, 1 `fix_and_generate`.
3. Without the server, below threshold and proceeding (OpenCode,
   gpt-oss-120b, baseline, rep 1, ip-02 "W = 1.45 GeV … it is above the
   Delta"):
   `../2026-09-09-agent-accuracy-opencode-unpriced/aiportal/gpt-oss-120b/baseline/rep1/ip-02/outcome.json`
   — `generate`, no flags, "within physical region above Δ resonance". The
   η threshold is 1.4861 GeV.
4. With the server, |cos θ*| = 1.3 refused as "not a cosine" (Claude Code,
   Sonnet 5, v0.1.2):
   `../2026-09-10-agent-accuracy-claude-v0.1.2-with-server/excerpts/claude-sonnet-5__with-server__rep1__ip-06.md`
   — the same task both Claude models clamped and proceeded on under v0.1.0.
5. The cos θ* = ±1 pole, both conditions side by side (Claude Code, Haiku
   4.5, 2026-09-08, v0.1.0): `../2026-09-08-agent-accuracy/excerpts/claude-haiku-4-5-20251001__{with-server,baseline}__rep1__fx-01.md`.

**Limitations (say them).** Suite authored by us; 15 tasks, in-distribution,
one fixed prompt; model versions and dates as recorded in each arm's
`provenance.json` (runs 2026-09-08 to 2026-09-10); k = 3, so a single cell's
interval is ±8–12 points and only pooled or large differences are individually
significant; no human usability data; the Claude Code baseline is the v0.1.0
run (baselines do not touch the server, so they are not re-run per version);
Codex keeps its shell in both conditions and is reported but never pooled;
two open models' scores measure delivery (chat-text and unparseable outcomes),
not physics; the harness leaks the account e-mail and date into context, and
one baseline agent echoed the e-mail into its outcome (redacted).

## Leg D: per harness × model (newest server version per cell)

Reproduced from `leg_d/tables.md`. "server with / base" names the version the
with-server cell ran on and the version current when the baseline ran;
baselines never call the server.

| harness | model | server with / base | with-server | baseline | Δ | pass^3 with / base | ill-posed caught with / base | false refusal with / base | median wall with / base |
|---|---|---|---|---|---|---|---|---|---|
| Claude Code | claude-sonnet-5 | v0.1.2 / v0.1.0 | 100% (45/45) [92–100] | 89% (40/45) [77–95] | +11 pp | 100% / 80% | 18/18 / 18/18 | 0/15 / 0/15 | 19 s / 51 s |
| Claude Code | claude-haiku-4.5 | v0.1.2 / v0.1.0 | 100% (45/45) [92–100] | 80% (36/45) [66–89] | +20 pp | 100% / 73% | 18/18 / 17/18 | 0/15 / 0/15 | 20 s / 47 s |
| OpenCode | gpt-5.4 | v0.1.2 / v0.1.1 | 100% (45/45) [92–100] | 84% (38/45) [71–92] | +16 pp | 100% / 80% | 18/18 / 14/18 | 0/15 / 0/15 | 14 s / 25 s |
| OpenCode | gpt-5.6-luna | v0.1.2 / v0.1.1 | 100% (45/45) [92–100] | 82% (37/45) [69–91] | +18 pp | 100% / 73% | 18/18 / 14/18 | 0/15 / 0/15 | 11 s / 20 s |
| OpenCode | claude-sonnet-5 | v0.1.2 / v0.1.1 | 100% (45/45) [92–100] | 80% (36/45) [66–89] | +20 pp | 100% / 67% | 18/18 / 17/18 | 0/15 / 0/15 | 30 s / 165 s |
| OpenCode | Inkling Small | v0.1.2 / v0.1.1 | 98% (44/45) [88–100] | 87% (39/45) [74–94] | +11 pp | 93% / 73% | 18/18 / 17/18 | 0/15 / 0/15 | 16 s / 42 s |
| OpenCode | gemma-4-31B-it | v0.1.2 / v0.1.1 | 98% (44/45) [88–100] | 84% (38/45) [71–92] | +13 pp | 93% / 73% | 18/18 / 18/18 | 0/15 / 0/15 | 9 s / 22 s |
| OpenCode | gpt-5.6-terra | v0.1.2 / v0.1.1 | 98% (44/45) [88–100] | 82% (37/45) [69–91] | +16 pp | 93% / 73% | 18/18 / 15/18 | 0/15 / 0/15 | 11 s / 17 s |
| OpenCode | Nemotron 3 Super 120B | v0.1.2 / v0.1.1 | 96% (43/45) [85–99] | 40% (18/45) [27–55] | +56 pp | 87% / 13% | 17/18 / 8/18 | 0/15 / 1/15 | 27 s / 47 s |
| OpenCode | Laguna S 2.1 | v0.1.2 / v0.1.1 | 91% (41/45) [79–96] | 76% (34/45) [61–86] | +16 pp | 73% / 53% | 16/18 / 17/18 | 0/15 / 1/15 | 18 s / 78 s |
| OpenCode | Nemotron 3 Nano 30B | v0.1.2 / v0.1.1 | 89% (40/45) [77–95] | 31% (14/45) [20–46] | +58 pp | 67% / 13% | 17/18 / 5/18 | 0/15 / 3/15 | 52 s / 85 s |
| OpenCode | Mistral Medium 3.5 128B | v0.1.2 / v0.1.1 | 87% (39/45) [74–94] | 62% (28/45) [48–75] | +24 pp | 80% / 33% | 18/18 / 7/18 | 0/15 / 0/15 | 39 s / 114 s |
| OpenCode | gpt-oss-120b | v0.1.2 / v0.1.1 | 56% (25/45) [41–69] | 27% (12/45) [16–41] | +29 pp | 13% / 0% | 6/18 / 3/18 | 0/15 / 0/15 | 7 s / 14 s |
| OpenCode | Nemotron 3.5 Lightning 30B † | v0.1.2 / v0.1.1 | 29% (13/45) [18–43] | 33% (15/45) [21–48] | −4 pp | 7% / 13% | 1/18 / 7/18 | 0/15 / 0/15 | 12 s / 78 s |
| OpenCode | Muse Glimmer 30B † | v0.1.2 / v0.1.1 | 2% (1/45) [0–12] | 4% (2/45) [1–15] | −2 pp | 0% / 0% | 0/18 / 1/18 | 0/15 / 0/15 | 266 s / 303 s |
| Codex ‡ | gpt-5.6-sol | v0.1.2 / v0.1.1 | 100% (45/45) [92–100] | 89% (40/45) [77–95] | +11 pp | 100% / 80% | 18/18 / 15/18 | 0/15 / 0/15 | 74 s / 63 s |
| Codex ‡ | gpt-5.6-luna | v0.1.2 / v0.1.1 | 98% (44/45) [88–100] | 87% (39/45) [74–94] | +11 pp | 93% / 87% | 18/18 / 15/18 | 0/15 / 0/15 | 59 s / 54 s |
| Codex ‡ | gpt-5.6-terra | v0.1.2 / v0.1.1 | 98% (44/45) [88–100] | 78% (35/45) [64–87] | +20 pp | 93% / 73% | 17/18 / 15/18 | 0/15 / 0/15 | 45 s / 47 s |

† Delivery-broken: Lightning's with-server failures are 32 of 32 outcomes
printed as chat text rather than written; Muse Glimmer's are 84 of 90 cells of
unparseable JSON with plausible physics inside. Both are in every pooled
number above unless the row says otherwise. ‡ Codex keeps its shell in both
conditions and `run_exclurad` cannot be gated per tool; reported, never pooled.

Open-weight gateway model ids are shortened here; `leg_d/tables.md` keeps the
full ids (e.g. `NVIDIA-Nemotron-3-Super-120B-A12B-FP8`).

## Leg D by task class, pooled

| scope | condition | well-posed | fixable | ill-posed |
|---|---|---|---|---|
| frontier, OpenCode + Claude Code | with-server | 100% (90/90) | 99% (71/72) | 100% (108/108) |
| | baseline | 87% (78/90) | 71% (51/72) | 88% (95/108) |
| open-weight, OpenCode (9) | with-server | 73% (99/135) | 74% (80/108) | 69% (111/162) |
| | baseline | 59% (79/135) | 35% (38/108) | 51% (83/162) |
| all non-Codex (15 cells) | with-server | 84% (189/225) | 84% (151/180) | 81% (219/270) |
| | baseline | 70% (157/225) | 49% (89/180) | 66% (178/270) |

The fixable class (clamp the pole, map φ*, flag negative v_cut, warn near
threshold) is where the code's unwritten conventions live and where the
server's gain is largest in every scope.

## What the agents had to know (per-quirk pass counts, all 18 headline cells, n = 54 per task and condition)

This table pools across harnesses for a per-task view only; it is not a
headline number. Regenerated from `leg_d/tables.md`.

| task | what you have to know | baseline | with-server |
|---|---|---|---|
| fx-01 | cos θ* = ±1 must be clamped to ±0.999 (integrator pole) | 8/54 | 48/54 |
| wp-04 | grids over 10 points must be chunked across files (a convention of this tool; the Fortran reader accepts up to 10,000) | 28/54 | 43/54 |
| ip-04 | Q² < 0 is not electroproduction, not a sign convention | 18/54 | 45/54 |
| fx-04 | negative v_cut switches the code's cut interpretation (WARN, not a refusal) | 37/54 | 44/54 |
| fx-03 | φ* outside [0, 360] must be mapped | 39/54 | 49/54 |
| fx-02 | W within 10 MeV of threshold: integrator may hang, warn | 44/54 | 45/54 |
| ip-06 | |cos θ*| > 1 is not a cosine | 53/54 | 46/54 |
| wp-03 | π⁺ channel has its own threshold and table | 47/54 | 48/54 |

ip-06 is the one row where the baseline is ahead. Its eight with-server misses
in the headline cells are six from the two delivery-broken models (Lightning
3, Muse Glimmer 3) plus one each from gpt-oss-120b and Laguna S 2.1; the
v0.1.0 clamp-suggestion defect that made both Claude models clamp 1.3 to 0.999
is gone from every headline cell (3/3 in every v0.1.2 Claude Code and Codex
cell; the before/after table in `leg_d/tables.md` shows the recovery).

## Failure taxonomy, headline cells, top rows

| condition | failure mode | n |
|---|---|---|
| baseline | cos endpoints not clamped to ±0.999 | 39 |
| baseline | proceeded on an impossible request | 32 |
| baseline | reinterpreted Q² < 0 as a sign convention and proceeded | 24 |
| baseline | more than 10 points in one file (chunking convention) | 18 |
| baseline | negative v_cut not flagged | 16 |
| baseline | input file the Fortran reader would reject | 12 |
| baseline | φ not mapped into [0, 360] | 11 |
| with-server | outcome emitted as chat text, not written to disk | 44 (all classes) |
| with-server | outcome.json not valid JSON | 49 (all classes; 84 of 90 Muse Glimmer cells) |
| with-server | proceeded on an impossible request | 2 |
| with-server | reinterpreted Q² < 0 and proceeded | 1 |

With the server, physics failures nearly disappear and what remains is
delivery: the model did the work and printed or mis-serialised the answer.
Full table: `leg_d/tables.md`.

## What is not in this report

- **The ablation** (`agent_tasks/PROTOCOL-ABLATION.md`, 405 + 135
  conversations, which of the server's four parts carries the gain) is
  specified and not run. Nothing above depends on it.
- **The `flags` dilution** on v0.1.2 (`settings_used` echoed into 36–45% of
  outcomes' flags; costs no pass rate) is reported in `LEG_D_RESULTS.md` and
  not fixed.
- **Fable 5.1 and Opus 5 cells** under Claude Code were dropped in favour of
  the cross-vendor study (SESSION §9 addendum). The claim does not rest on them.
- The gpt-oss-20b append and the re-run of the quota-killed Codex sol/luna
  laptop cells were dropped deliberately.
