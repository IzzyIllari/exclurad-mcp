# Leg D run protocol

How an agent-accuracy run is conducted so that different models and
conditions are comparable. The suite is `tasks.json` (versioned; results
must record the suite version). Scoring is `../score_agent_run.py` —
deterministic checks only, no LLM judges.

## Conditions

Each model runs the full suite under two conditions:

- **with-server** — the agent has the exclurad MCP server registered and is
  told to use it.
- **baseline** — the agent has no server; it gets the EXCLURAD Fortran
  source, the repository README, and file-writing ability. Nothing else.

Same prompts, same order, one task per fresh conversation (no learning
across tasks). Temperature and model ID recorded per run.

## Prompt template

Each task's conversation starts with exactly:

> You are helping a nuclear physicist run the EXCLURAD radiative-corrections
> code. Request: {request}
>
> When you are done, write an `outcome.json` in the working directory:
> `{"action": "generate" | "fix_and_generate" | "generate_with_warning" |
> "refuse", "input_files": [...], "flags": [...], "explanation": "..."}`.
> Write any EXCLURAD input files you produce next to it. If the request is
> physically impossible, refuse and say why. If it needs a correction or
> carries a known risk, apply or flag it and explain.

`{request}` is the task's `request` field, verbatim.

## Collecting a run

One directory per run: `<run>/<task-id>/outcome.json` plus any input files.
Score with:

```bash
PYTHONPATH=src python3 benchmarks/score_agent_run.py \
    --suite benchmarks/agent_tasks/tasks.json \
    --run-dir <run> --json <run>/scores.json
```

A task passes only if the direction (proceed/refuse), the file validity
(parseable, ≤10 points/file, correct header, preflight-clean), the required
fixes/flags, and the required explanation facts all check out.

## Reference runs

Two synthetic runs pin the scorer's dynamic range (regenerate with the
script in the session scratchpad or by hand):

- a **perfect** protocol-following run scores 15/15;
- a **naive** run that proceeds verbatim on every request scores 5/15
  (all well-posed pass; every fixable and ill-posed task fails with the
  physics reason named). This is the expected shape of a no-server baseline
  that never validates.

## Ground truth hygiene

`../verify_task_ground_truth.py` re-derives every task label from
`validators.py` (exit 0 = consistent). Run it whenever the suite or the
validators change. Suite task ip-04 exists because designing it exposed a
real validator gap: before 2026-07-22, a negative-Q² request passed every
preflight gate except the table-coverage warning (`check_q2_positive` was
added, with tests, as a result).

## What the study reports

Per model × condition: pass rate overall and by class, plus the ill-posed
catch rate (the safety-critical number: fraction of impossible requests
refused with the physics stated). The claim under test: with the server,
pass rates converge across models; without it, they diverge — correctness
lives in the tooling, not the model.
