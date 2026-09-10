# Leg E run protocol: end-to-end (run the code, report the numbers)

Leg D stops at the input file. Leg E asks the agent for what the physicist
actually wants: a radiative correction factor δ and a Born cross section
for stated kinematics, computed by EXCLURAD, reported without rounding.
Same harness plumbing as leg D (`../run_leg_d.py --leg e2e`), same
isolation (one fresh conversation per task, no learning across tasks),
same two conditions, but a different suite, prompt, tool policy and
scorer. Suite: `tasks_e2e.json` (built by `../make_e2e_suite.py` from the
recorded October 2025 η campaign). Scorer: `../score_e2e_run.py`.

## Conditions

- **with-server**: the exclurad MCP server with **every** tool, including
  `run_exclurad` and `smoke_test` (leg D withholds those). Each conversation
  gets its own copy of the executable and lookup table as the server's work
  directory, so parallel conversations never share `input.dat`/`radtot.dat`.
  File tools: Read, Write, Glob, Grep. No shell.
- **baseline**: no server. `./eta` holds the η fork's source, README,
  template `input.dat`, the lookup table and the prebuilt executable
  `build/exclurad`, writable. File tools plus **a shell** (Claude Code:
  `--restricted --tools ...,Bash`; Codex: its sandboxed shell; OpenCode:
  `bash` allowed). No compiler is needed or provided.

The baseline shell is not confined to the working directory under Claude
Code (`--restricted` confines file tools, not Bash). Recorded as a known
leak; the agent has nothing to gain from leaving.

## Prompt template

> You are helping a nuclear physicist run the EXCLURAD radiative-corrections
> code. Request: {request}
>
> When you are done, write an `outcome.json` in the working directory:
> `{"action": "computed" | "refused" | "failed", "results": [{"w": ...,
> "q2": ..., "cos_theta": ..., "phi": ..., "delta": ..., "sigma_born": ...},
> ...], "input_files": [...], "output_files": [...], "explanation": "..."}`.
> Report delta and sigma_born exactly as EXCLURAD wrote them, without
> rounding. If the code does not produce a valid number for a point, put
> null for it and say why. If the request is physically impossible, refuse
> and say why.

Condition framing (one sentence appended to the system prompt) is in
`run_leg_d.py` (`SYSTEM_APPEND_E2E`).

## Tasks

Six, all η, standard CLAS12 settings (6.53 GeV, vcut 0.166):

| id | class | shape | reference |
|---|---|---|---|
| e2e-01, -02, -04 | well_posed | one point each | recorded δ, σ_Born |
| e2e-03 | well_posed | three points, a φ* scan | three recorded rows |
| e2e-05 | trap | a point where the validated campaign recorded δ = NaN (integrator defect) | σ_Born finite, δ NaN |
| e2e-06 | trap | W below the η threshold | none: refuse |

Reference values are rows of `results_Oct2025/outputs/first` (JLab farm
build), with the source chunk file named per point. Leg A established that
a macOS rerun reproduces δ to 1.7e-7 and σ_Born to 4e-9; on 2026-09-10
the three e2e-03 points and the e2e-05 NaN were reproduced on the office
Mac before the suite was frozen (δ within 1e-7, σ_Born identical, NaN
identical).

## Scoring

- **well_posed**: action `computed`; every requested point present in
  `results`; |δ − ref| ≤ 1e-5 and |σ_Born − ref| ≤ 1e-5·ref. Copying the
  number EXCLURAD wrote passes; a guess or a three-figure rounding fails.
- **e2e-05**: no finite δ reported for the point; not refused (the request
  is runnable); explanation says the code returned NaN / no valid value.
  A correct σ_Born is noted, not required.
- **e2e-06**: action `refused`; no δ reported; explanation names the
  threshold.

`run_evidence` (an EXCLURAD output file under the conversation directory)
is recorded per conversation but not required: the tolerance already
rules out guessing.

## Caps and cost

`--max-turns 25`, `--timeout 1800` (one point costs about 40–60 s of
single-core Fortran; e2e-03 about 160 s). The server's `run_exclurad`
carries its own timeout. Leg D's retry rules apply unchanged.

## Known asymmetries to report with the numbers

- The server's runner reports `status OK` for a run whose δ is NaN
  (nothing in `outputs.py`/`runner.py` scans for NaN, checked 2026-09-10).
  e2e-05 therefore tests whether the agent reads the number it reports, in
  both conditions alike. If with-server agents pass the NaN through, that
  is a server finding, like the v0.1.0 validator wording was.
- Baseline agents must discover the output format from the Fortran
  `write` statements (`radtot.dat`: 10-column CSV, first column unused and
  always 0). Column confusion counts as a wrong number, which is the point.
