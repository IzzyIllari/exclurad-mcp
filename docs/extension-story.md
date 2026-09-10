# What it took to add the η channel, and what the server captures

Companion to the leg D benchmark (`benchmarks/benchmark-plan.md`). Leg D
measures whether agents get the *inputs* right; this note is about the
other half of the case for the server: the knowledge needed to run and
extend EXCLURAD had left with the people who wrote it, it took years to
recover, and the server is where that knowledge now lives in machine-
readable form. Every number below comes from the two checkouts the
benchmark uses (upstream `JeffersonLab/exclurad` at b6fda2b, the η fork
`IzzyIllari/exclurad` at 145e2e1) and from the server's own slot registry.

## 1. The timeline, from git

| date | event | evidence |
|---|---|---|
| 2003-01-07 | last upstream change to the Fortran (π⁺ only) | `latest update` comment in `exclurad.F` |
| 2022-02-10 | fork created; upstream history ends at b6fda2b | fork git log |
| 2024-02-02 | first working η build | `build/exclurad-Working-2Feb24.o`, header comment `Feb.2, 2024` |
| 2024-02-19 | η source changes committed with the first grid scripts | ce2da64, "Includes changes to exclurad.F" |
| 2025-11 to 2026-03 | slurm array scripts, chunked-input generator, production grid (789 866 rows) | 18dcce6, 024a241 |
| 2026-07-21 | full merged dataset, W to 2.211 GeV (1 915 686 rows) | 145e2e1 |

Two years from fork to a working η executable, and two more to a
production grid. Nobody who wrote the 2003 code was available for any of it.

## 2. The diff that made η work

`diff` of the fork's Fortran against upstream, ignoring the lookup table:

| file | changed lines | what changed |
|---|---|---|
| `exclurad.F` | 41 | meson mass at **four separate sites** (`amhad/amunm`, three `DATA XMPIP/XMPI0` statements); integration tolerance `ot` 1d-2 → 1d-3; table-header `FORMAT` statement; two output `write` formats |
| `mpintp.inc` | ~20 | `NVAR1 × NVAR2` grid dimensions of the table, plus a commented history of every table generation tried |
| `spp.inc`, `fint.F` | 0 | unchanged |
| `maid07-PPpi.tbl` | whole file (9.7 MB) | EtaMAID-2023 multipoles **under the pion filename**, because the Fortran hardcodes the name |

Forty-one lines. None of them is hard to type. Every one of them is hard
to *find*: the mass appears in four routines that must agree, the grid
dimensions in an include file must match a table whose header layout is
read by a `FORMAT` statement 4400 lines away, and the table itself keeps
a misleading name. That is the tacit knowledge the fork's four years went
into, and it appears nowhere in the code as documentation.

Around the 41 lines sit the operational conventions that took as long to
learn: cos θ* = ±1 crashes the integrator, so clamp to ±0.999; a point
below threshold or too close to it can hang the run or exit cleanly with
no result; the input needs two blank lines between header and points; a
NAG error line in known-good runs is inert. These are the quirks in the
server's `list_channels` output, and the leg D suite tests each one.

## 3. What the server encodes

`describe_build_slots` lists 16 slots in the two templated files. Nine are
substantive; seven are cosmetic (comments and whitespace) and exist only
so `generate_build` reproduces each checkout byte-for-byte, which
`verify_against` checks.

| slot | file | η value | π⁺ value |
|---|---|---|---|
| `meson_mass_amhad` (site 1 of 4) | exclurad.F | 0.54786 | 0.13957 |
| `meson_mass_born_1` (site 2 of 4) | exclurad.F | 0.54786 | 0.1395 / 0.1349 |
| `meson_mass_born_2` (site 3 of 4) | exclurad.F | 0.54786 | 0.139563 / 0.1349630 |
| `meson_mass_born_3` (site 4 of 4) | exclurad.F | 0.54786 | 0.1395 / 0.1349 |
| `integration_tolerance` | exclurad.F | 1d-3 | 1d-2 |
| `table_header_format` | exclurad.F | A6,f6.4,A8,f4.2 | A8,f4.2,A7,f7.5 |
| `output_format_radsigpl` | exclurad.F | CSV F12.6 | fixed 5f6.2,2g11.3 |
| `output_format_radtot` | exclurad.F | 10-col CSV F16.10 | 7-col fixed |
| `nvar_grid_dims` | mpintp.inc | 101 × 92 (EtaMAID-2023) | 101 × 93 (MAID07) |

Plus, outside the Fortran, the channel registry (`channels.py`): threshold
W_min = m_p + m_meson, which lookup table a (model, channel) pair actually
opens and what it really contains, the detected-hadron flag, defaults for
beam energy and vcut, and the quirks list. The validators
(`validators.py`) turn the quirks into checks an agent gets back before a
file is written; leg D shows agents obey them (v0.1.1: the wording of
those checks matters, see PROTOCOL.md).

## 4. What η′ would take

Same reaction class, same code paths, one heavier meson. With the server:

1. **Channel entry.** `M_ETAPRIME = 0.95778`; threshold m_p + m_η′ =
   1.8961 GeV; `ivec`, model, defaults copied from η. One dataclass.
2. **Slot values.** The four mass sites get one number; tolerance and
   output formats inherit η's. `generate_build("etaprime")` renders the
   sources; `verify_against` a hand-edited reference confirms them.
3. **The table.** An η′ multipole table (EtaMAID-2018 η′ or whatever
   becomes available) written to the hardcoded filename, with
   `nvar_grid_dims` and `table_header_format` set to match its layout.
   `resolve_tables` then reports what the build actually opens.
4. **Validation.** `preflight_check` and the leg D suite run unchanged
   against the new threshold; leg A's regression harness gives the
   byte-level check against a reference run once one exists.

Step 3 is the real bottleneck and the server cannot produce it: the
physics input has to come from the MAID group. What the server removes is
everything else, which is what the four years were spent on. The honest
one-line version: the server does not know η′ physics, it knows where
EXCLURAD hides its assumptions.

## 5. Evidence that the captured knowledge transfers

From the leg D headline cells (six model × harness cells, k = 3, pooled):

| what you have to know | agents reading the Fortran | agents with the server |
|---|---|---|
| cos θ* = ±1 must be clamped | 5/18 | 18/18 |
| grids over 10 points are chunked | 8/18 | 17/18 |
| Q² < 0 is not a sign convention | 7/18 | 17/18 |
| negative vcut changes the cut's meaning | 12/18 | 18/18 |

A frontier model with the source in front of it gets the pole clamp right
one time in four. The same model with the server gets it right every time,
at a third to a seventh of the cost per correct result
(`benchmarks/report_leg_d_combined.py`, cost table).
