# Leg D, Codex arm (gpt-5.6-sol / terra / luna), k=3, server v0.1.1

Run on the office Mac (Codex 0.153.4, ChatGPT login; `--expect-harness-version
0.153.4`), 270 conversations, 0 timeouts, 0 missing outcomes, 0 bypass
attempts. Codex records tokens only; the cost columns read n/a. This run
predates the runner's final-text fallback (de511e4 was committed after the
launch), so `result.json` final_text is null throughout; the transcripts
carry the agent messages.

Protocol deviations, per PROTOCOL.md "Harnesses": the shell is available in
both conditions (workspace-write sandbox); gpt-5.6-sol is Codex-only, so its
row confounds harness and model. Terra and luna also ran under OpenCode
(2026-09-09-agent-accuracy-opencode-priced) for the harness-effect row.

Finding: every model fails ip-04 (Q2 = -0.5) in BOTH conditions, 18/18
conversations. With the server, the agents call preflight_check, get the
q2_positive FAIL whose suggestion reads "Use a positive Q2 ...", and
generate at +0.5 with a "sign convention corrected" flag. Under OpenCode the
same models refused ip-04 with-server 17/18. This is the third validator
suggestion string that reads as an instruction (after the |cos|>1 clamp and
the below-threshold W shift fixed in v0.1.1); see the combined report.
