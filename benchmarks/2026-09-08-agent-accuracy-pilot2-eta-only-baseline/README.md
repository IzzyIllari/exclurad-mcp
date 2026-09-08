# Leg D pilot 2 — 2026-09-08

Sonnet 5, both conditions, k = 1, 30 conversations, $2.73 list price,
with the fixed harness (auto-memory off, `--restricted`). Scored 14/15
with-server, 13/15 baseline. This is the run behind the cost projection
reported before the main study was launched ($67 list price for
4 models × 2 conditions × 15 tasks × k = 3).

Two findings changed the protocol before the main run:

- The baseline working directory held the η fork only, and the sonnet
  baseline **refused the π⁺ task wp-03** on the reasonable grounds that
  the checkout it could see could not run pions. The main run gives the
  baseline both source trees (`./eta`, `./pion`) and gives the server
  both work directories.
- On ip-06 (cos θ* = 1.3), the with-server sonnet **clamped the impossible
  cosine to 0.999 and proceeded**, because `preflight_check` reports
  |cos θ*| > 1 with the pole message ("cannot evaluate exactly at the
  poles; clamp to ±0.999"). That is a validator wording defect the
  benchmark surfaced; it was left untouched for the main run and is a
  follow-up.

Superseded by `../2026-09-08-agent-accuracy/` (same harness plus the
π⁺ tree).
