# Leg E shakedown (2026-09-10, office Mac, sonnet, e2e-01 + e2e-06, k=1)

First live run of `run_leg_d.py --leg e2e`. Not used in any table.

- with-server e2e-01: pass in 84 s / 7 turns; delta 0.9159587896 vs reference
  0.9159587883 (1.3e-9), sigma_born identical. Tools: preflight_check,
  generate_input, run_exclurad, describe_outputs, parse_output.
- with-server e2e-06: refused, threshold named, 17 s.
- baseline e2e-06: refused after reading the mass DATA statements and
  computing the threshold itself, 217 s / 20 turns.
- baseline e2e-01: NO outcome. 646 s, hit the 25-turn cap with the correct
  radtot.dat already on disk (delta 0.9159587896). The trace is the tacit-
  knowledge story in miniature: ran `./build/exclurad < input_point.dat`
  (the code ignores stdin and reads the hardcoded input.dat), computed the
  template's three points instead, discovered this from the OPEN statement,
  reran, was killed by the 2-minute shell tool timeout, reran in the
  background, polled, then ran out of turns while grepping for the
  radtot column layout.

Consequence: leg E's turn cap is 50 (both conditions), set in the runner's
leg spec after this run. The scorer's summary schema was also aligned with
leg D's (`n_tasks`, `by_class`).
