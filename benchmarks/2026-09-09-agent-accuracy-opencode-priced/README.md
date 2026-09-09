# Leg D stage 1 — OpenCode priced arm (2026-09-09)

360 conversations: 4 models × 2 conditions × 3 reps × 15 tasks, OpenCode
1.18.28, exclurad-mcp 0.1.1, LANL AIPortal gateway.

| model | with-server | baseline |
|---|---|---|
| aiportal/aws-gov.gpt-5.6-luna | 98% (44/45) [88–100] | 82% (37/45) [69–91] |
| aiportal/aws-gov.gpt-5.6-terra | 100% (45/45) [92–100] | 82% (37/45) [69–91] |
| aiportal/aws-gov.gpt-5.4 | 100% (45/45) [92–100] | 84% (38/45) [71–92] |
| aiportal/aws.claude-sonnet-5 | 98% (44/45) [88–100] | 80% (36/45) [66–89] |

False refusal of a well-posed request: 0/15 in both conditions, all four
models. Run integrity: 360/360 scored, no `opencode_server_errors.log`, no
silent agent fallbacks, no timeouts, no bypass attempts.

claude-opus-5 was dropped before it ran, to conserve API budget. A guard
stopped the runner at the sonnet→opus boundary; opus produced a 250-byte
transcript with no token or cost events and its stub directory was removed.

Two claude-sonnet-5 baseline conversations were in flight at that kill and
were refilled with `--resume`. They are the only 2 of the 360 whose
`opencode.json` carries the `MODEL_LIMITS` provider block, which landed
between the original run and the resume. It sets token ceilings only for
`meta.llama3-8b` and `mistral7b`, neither of which appears in this arm, so
it is inert here.

## The claude-sonnet-5 baseline latency: what the long conversations were

**Question.** Baseline median wall for claude-sonnet-5 is 164 s here against
51 s median / 110 s max under Claude Code, and several conversations ran
~305 s and failed. If a request-level cutoff ended them, those cells are
infrastructure results and the cross-harness latency comparison is
confounded by the gateway.

**Answer: no cutoff fired, and the model genuinely worked that long.** The
latency figure stands as model behaviour. Details:

- **The longest *successful* baseline conversation ran 639.6 s** (rep2/fx-02,
  24 turns, outcome.json written and scored). Also 637.3 s, 627.4 s, 564.4 s,
  452.0 s, 440.3 s. A ~300 s request cutoff cannot coexist with a 639 s
  success, so no such cutoff exists on this path.
- **No timeout fired anywhere.** `timed_out` is `False` in all 45 sonnet
  baseline conversations. The runner's own wall-clock limit is
  `--timeout 900` (default, unchanged); the longest conversation used 71% of
  it.
- **No provider timeout is configured**, in either `~/.config/opencode/
  opencode.jsonc` or the generated per-conversation `opencode.json`. The MCP
  block carries `timeout: 30000` but that governs exclurad server calls, which
  the baseline condition does not have.
- **The failures are not clustered at a boundary.** Wall times of the ten
  failed conversations: 193.9, 217.9, 236.1, 241.1, 249.9, 289.5, 304.2,
  304.4, 305.7, 314.8 s. A cutoff would pile them on one value. The ~305 s
  figure was three conversations near each other, not a limit.

**What actually ended them.** All ten failures carry the identical final
event, a Bedrock API rejection:

```
litellm.BadRequestError: BedrockException - {"message":"The model returned
the following errors: This model does not support assistant message prefill.
The conversation must end with a user message."}
Received Model Group=aws.claude-sonnet-5
```

Every one has `num_turns: 25` exactly — the runner's `--max-turns 25` step
cap. When OpenCode reaches the cap while the last assistant message is still
a tool call, it issues a request whose message list ends with an assistant
message, and the Bedrock-hosted Claude endpoint refuses assistant prefill.
`stderr.txt` is empty in every case; the error appears only as the last
`{"type":"error"}` event in `transcript.jsonl`.

So this is a harness × endpoint interaction at the step cap, not a timeout
and not the model failing. The conversation was doing real work up to that
point — a failing fx-01 attempt made 40 tool calls (16 read, 21 grep,
3 glob) reading the Fortran source, which is also why baseline is slow: with
no server to ask, the model greps for the input-format conventions.

**Affected conversation ids** (10 conversations across 4 cells):

| conversation | attempts | outcome |
|---|---|---|
| `aws.claude-sonnet-5/baseline/rep1/fx-01` | 3 (`.attempt1`, `.attempt2`, final) | scored failure |
| `aws.claude-sonnet-5/baseline/rep2/fx-01` | 3 | scored failure |
| `aws.claude-sonnet-5/baseline/rep3/fx-01` | 3 | scored failure |
| `aws.claude-sonnet-5/baseline/rep2/fx-04` | 2 (`.attempt1` failed) | recovered, scored pass |

These are the 3 "no outcome.json written" rows in the stage 1 failure
taxonomy. All are baseline fx-01; no with-server conversation was affected,
and no other model was affected.

**Can the limit be raised?** Yes — it is `--max-turns`, default 25, ours. The
successful baseline conversations used 4–24 turns, so fx-01 is the only task
that exceeded it, and a higher cap would probably let it finish. It is not
raised here because the cap applies to every model and both conditions, so
changing it invalidates comparability with the 357 conversations already
scored; the whole arm would have to be re-run. Recorded as a known limitation
instead.

**What this does and does not settle for the cross-harness comparison.** It
excludes a gateway request cutoff as the explanation for the 164 s vs 51 s
difference — that comparison is not confounded in the way suspected. It does
not explain the difference. Candidate causes not investigated here: gateway
round-trip latency, differences in the tool surface each harness exposes, and
differences in system prompt length. Anyone putting the two medians on one
slide should treat the harnesses as differing in more than the server.

**One inefficiency this exposed.** `classify()` in `run_leg_d.py` treats
`error_during_execution` as retryable, so each fx-01 cell burned all three
attempts on a failure that reproduces exactly — 9 conversations and roughly
45 minutes of wall time for 3 scored cells. The prefill rejection is
deterministic at the step cap and cannot succeed on retry. Not changed
mid-study; noted for the protocol.
