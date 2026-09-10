# Codex shakedown on the office Mac (2026-09-09, luna, wp-01 + ip-04, k=1)

Confirms the Codex arm runs on this machine (Codex 0.153.4, ChatGPT login,
server v0.1.1) before stage 3 was launched here rather than on the LANL
laptop. 4/4 conversations completed: MCP tools called with-server, files
and outcome.json written, tokens parsed. wp-01 passes in both conditions;
ip-04 fails in both with the same Q² sign-convention reinterpretation seen
on every other harness. Not used in any table. Note: this run predates the
absolute-path fix (de511e4), so its result.json final_text fields are null.
