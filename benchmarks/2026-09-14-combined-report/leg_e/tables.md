# Leg E (end-to-end) tables

Runs: 2026-09-10-end-to-end-claude, 2026-09-10-end-to-end-codex, 2026-09-10-end-to-end-claude-v0.1.2, 2026-09-10-end-to-end-codex-v0.1.2. 270 conversations.

## Pass rate per harness × model × condition

| harness | model | condition | pass rate | well-posed | trap | NaN trap | median wall | cost | timeouts |
|---|---|---|---|---|---|---|---|---|---|
| Claude Code | claude-haiku-4.5 | with-server | 92% (33/36) [78–97] | 22/24 | 11/12 | 5/6 | 76 s | $1.19 | 0 |
| Claude Code | claude-haiku-4.5 | baseline | 78% (14/18) [55–91] | 9/12 | 5/6 | 2/3 | 270 s | $2.79 | 1 |
| Claude Code | claude-sonnet-5 | with-server | 100% (36/36) [90–100] | 24/24 | 12/12 | 6/6 | 82 s | $3.12 | 0 |
| Claude Code | claude-sonnet-5 | baseline | 100% (18/18) [82–100] | 12/12 | 6/6 | 3/3 | 253 s | $6.23 | 0 |
| Codex | gpt-5.6-luna | with-server | 86% (31/36) [71–94] | 19/24 | 12/12 | 6/6 | 146 s | n/a | 0 |
| Codex | gpt-5.6-luna | baseline | 94% (17/18) [74–99] | 11/12 | 6/6 | 3/3 | 246 s | n/a | 0 |
| Codex | gpt-5.6-sol | with-server | 100% (36/36) [90–100] | 24/24 | 12/12 | 6/6 | 142 s | n/a | 0 |
| Codex | gpt-5.6-sol | baseline | 100% (18/18) [82–100] | 12/12 | 6/6 | 3/3 | 162 s | n/a | 0 |
| Codex | gpt-5.6-terra | with-server | 97% (35/36) [86–100] | 24/24 | 11/12 | 5/6 | 117 s | n/a | 0 |
| Codex | gpt-5.6-terra | baseline | 94% (17/18) [74–99] | 11/12 | 6/6 | 3/3 | 140 s | n/a | 0 |

## Pooled

| condition | n | pass rate | well-posed | trap |
|---|---|---|---|---|
| with-server | 180 | 95% (171/180) [91–97] | 113/120 | 58/60 |
| baseline | 90 | 93% (84/90) [86–97] | 55/60 | 29/30 |

## Failure taxonomy

| condition | failure mode | n |
|---|---|---|
| baseline | wrong radtot column (sigma_born) | 2 |
| baseline | delta off (no matching run on disk) | 2 |
| baseline | no outcome (timeout / turn cap) | 1 |
| baseline | refused a runnable point | 1 |
| with-server | asked for rc_mode=1 (leading-log), server reported NO_TAI | 5 |
| with-server | wrong beam energy assumed (10.6 GeV) | 3 |
| with-server | other: no execution evidence: the NaN was not observed fr | 1 |

## Every failure

| harness | model | condition | rep | task | mode | scorer |
|---|---|---|---|---|---|---|
| Claude Code | claude-haiku-4.5 | with-server | 1 | e2e-03 | wrong beam energy assumed (10.6 GeV) | delta 0.9042903591 vs reference 0.9296648137 (|diff| 2.54e-02 > 1e-05); sigma_born 0.01609 |
| Claude Code | claude-haiku-4.5 | with-server | 3 | e2e-02 | wrong beam energy assumed (10.6 GeV) | delta 0.9237048654 vs reference 0.9509747297 (|diff| 2.73e-02 > 1e-05); sigma_born 0.00757 |
| Claude Code | claude-haiku-4.5 | with-server | 3 | e2e-05 | wrong beam energy assumed (10.6 GeV) | reported a finite delta (0.8612376535) where EXCLURAD returns NaN; explanation mentions no |
| Claude Code | claude-haiku-4.5 | baseline | 1 | e2e-01 | no outcome (timeout / turn cap) | no outcome.json |
| Claude Code | claude-haiku-4.5 | baseline | 1 | e2e-04 | wrong radtot column (sigma_born) | sigma_born 0.3349910177 vs reference 0.005590767 |
| Claude Code | claude-haiku-4.5 | baseline | 1 | e2e-05 | refused a runnable point | refused a runnable request instead of running it and reporting the NaN |
| Claude Code | claude-haiku-4.5 | baseline | 3 | e2e-01 | delta off (no matching run on disk) | delta 0.9154973987072363 vs reference 0.9159587883 (|diff| 4.61e-04 > 1e-05); sigma_born 0 |
| Codex | gpt-5.6-terra | baseline | 3 | e2e-03 | wrong radtot column (sigma_born) | sigma_born 0.015244 vs reference 0.0151944029; sigma_born 0.017588 vs reference 0.01750697 |
| Codex | gpt-5.6-luna | with-server | 1 | e2e-01 | asked for rc_mode=1 (leading-log), server reported NO_TAI | direction: expected computed, agent chose failed; delta missing for phi=72.0; sigma_born m |
| Codex | gpt-5.6-luna | with-server | 1 | e2e-04 | asked for rc_mode=1 (leading-log), server reported NO_TAI | delta missing for phi=36.0; sigma_born missing for phi=36.0 |
| Codex | gpt-5.6-luna | with-server | 2 | e2e-01 | asked for rc_mode=1 (leading-log), server reported NO_TAI | direction: expected computed, agent chose failed; delta missing for phi=72.0; sigma_born m |
| Codex | gpt-5.6-luna | with-server | 2 | e2e-02 | asked for rc_mode=1 (leading-log), server reported NO_TAI | direction: expected computed, agent chose failed; delta missing for phi=300.0; sigma_born  |
| Codex | gpt-5.6-luna | with-server | 3 | e2e-01 | asked for rc_mode=1 (leading-log), server reported NO_TAI | direction: expected computed, agent chose failed; delta missing for phi=72.0; sigma_born m |
| Codex | gpt-5.6-luna | baseline | 3 | e2e-04 | delta off (no matching run on disk) | delta 1.141 vs reference 1.1413042139 (|diff| 3.04e-04 > 1e-05) |
| Codex | gpt-5.6-terra | with-server | 1 | e2e-05 | other: no execution evidence: the NaN was not observed fr | no execution evidence: the NaN was not observed from an EXCLURAD run |
