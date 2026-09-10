# Leg E (end-to-end), Codex, gpt-5.6 sol / terra / luna, k=3, server v0.1.1

108 conversations on the office Mac (Codex 0.153.4 pinned), tokens only,
0 timeouts. Scored by `score_e2e_run.py` (PROTOCOL-E.md).

| model | with-server | baseline |
|---|---|---|
| gpt-5.6-sol | 18/18 | 18/18 |
| gpt-5.6-terra | 18/18 | 17/18 |
| gpt-5.6-luna | 13/18 | 17/18 |

All three models report the NaN trap correctly in both conditions (9/9
each), and refuse the below-threshold point.

Luna's five with-server misses have one cause, and it is partly the
server's: luna passed `rc_mode=1` (the factorised leading-log approximation)
to `generate_input` in 11 of its 15 computable conversations, where the
references and every other model used the default 0 (full calculation).
The run itself completes and writes radtot.dat, but the server's runner
classifies it `NO_TAI` ("silent N/A"), because its success heuristic looks
for the `tai:` integration lines that only the full mode prints. Luna then
reported `failed` with delta null (4 cases) or left the values missing (1);
in 3 other conversations it noticed, reran with rc_mode=0 and passed. Sol
did the same once and recovered. Two server findings for the post-study
list: the `rc_mode` parameter reads like a boolean and is easy to set to 1
by mistake, and the runner's NO_TAI classification is wrong for mode 1
(it should look at the output files, not stdout).

Baseline misses: terra rep3 e2e-03 reported sigma_Born rounded to five
figures (the scorer's 1e-5 relative tolerance fails 0.015244 vs
0.0151944029); luna rep3 e2e-04 reported delta rounded to 1.141. Both are
"report the number exactly as written" failures rather than wrong runs.
