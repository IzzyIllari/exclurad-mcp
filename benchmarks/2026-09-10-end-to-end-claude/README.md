# Leg E (end-to-end), Claude Code, sonnet + haiku, k=3, server v0.1.1

72 conversations on the office Mac, $11.13 list price, turn cap 50,
timeout 1800 s. Scored by `score_e2e_run.py` against recorded October-2025
campaign rows (PROTOCOL-E.md).

| model | with-server | baseline |
|---|---|---|
| sonnet-5 | 18/18 | 18/18 |
| haiku-4.5 | 15/18 | 14/18 |

Sonnet is perfect in both conditions; its baseline conversations cost about
four times more and take two to five times longer (it discovers the
hardcoded `input.dat`, the shell-tool timeout, and the radtot column layout
on its own each time). Sonnet with-server reports the NaN trap correctly
(delta null, sigma_Born correct, explanation names the NaN) in 3/3.

Haiku's failures, every one inspected:

- with-server (3): all three passed `beam_gev=10.6` to `generate_input`
  ("CLAS12 standard beam energy") instead of using the channel default of
  6.53 GeV that `list_channels` reports and the campaign used. It never
  called `list_channels`. The numbers it reported are correct for 10.6 GeV
  (delta off by 2.5e-2), and at 10.6 GeV the e2e-05 point is not NaN, so it
  reported a finite delta there. The beam energy of "standard CLAS12
  settings" is itself tacit knowledge the server encodes; an agent that does
  not ask the tool for its defaults gets a silently wrong number.
- baseline (4): one wall-clock timeout at 1800 s with no outcome; one
  `sigma_born` read from the wrong radtot column (0.335, the Born asymmetry,
  delta correct); one false refusal of the NaN-trap point as "unphysical"
  near threshold; one conversation at the 50-turn cap that reported a
  delta 4.6e-4 off and a rounded sigma_Born (no matching run on disk).

Note for the report: the with-server beam-energy failures are wrong
numbers delivered with confidence, which is the failure mode leg E exists
to measure; they are not scorer artefacts. The suite wording ("standard
CLAS12 settings" in e2e-02/03/05, explicit 6.53 GeV in e2e-01/04) is kept
as written for the study; a follow-up suite version may state the beam
energy everywhere.
