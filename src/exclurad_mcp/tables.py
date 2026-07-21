"""Lookup-table introspection and hardcoded-filename resolution.

The Fortran hardcodes which .tbl file it opens based on the model flag and
channel (exclurad.F, data_file assignments around line 4266). Worse, the
filenames are historical aliases: in the eta configuration, 'maid07-PPpi.tbl'
actually contains EtaMAID-2023 eta multipoles. This module makes both facts
machine-readable, and scans the real grid coverage out of a table file so the
validator checks against ground truth instead of documentation.
"""

import re
from pathlib import Path

from .channels import ChannelConfig

# .tbl block headers look like:  W =  1.4856  Q2 =  0.00
_HEADER_RE = re.compile(r"^\s*W\s*=\s*([\d.Ee+-]+)\s+Q2\s*=\s*([\d.Ee+-]+)")


def scan_table_grid(table_path: str | Path) -> dict:
    """Extract the (W, Q2) grid actually present in a lookup table."""
    path = Path(table_path)
    if not path.exists():
        raise FileNotFoundError(f"Lookup table not found: {path}")
    w_vals: set[float] = set()
    q2_vals: set[float] = set()
    n_blocks = 0
    with path.open() as f:
        for line in f:
            m = _HEADER_RE.match(line)
            if m:
                w_vals.add(float(m.group(1)))
                q2_vals.add(float(m.group(2)))
                n_blocks += 1
    if not w_vals:
        raise ValueError(f"No 'W = ... Q2 = ...' block headers found in {path}")
    return {
        "table": str(path),
        "n_blocks": n_blocks,
        "w_range": (min(w_vals), max(w_vals)),
        "q2_range": (min(q2_vals), max(q2_vals)),
        "n_w": len(w_vals),
        "n_q2": len(q2_vals),
        "w_values": sorted(w_vals),
        "q2_values": sorted(q2_vals),
    }


def resolve_table(ch: ChannelConfig, work_dir: str | Path) -> dict:
    """Report which table file the Fortran will open for this channel and what
    it actually contains, plus its scanned grid if the file is present."""
    work = Path(work_dir)
    table_path = work / ch.table_file
    info: dict = {
        "channel": ch.key,
        "model_flag": ch.model,
        "hardcoded_filename": ch.table_file,
        "actual_content": ch.table_actual_content,
        "exists": table_path.exists(),
        "path": str(table_path),
    }
    if table_path.exists():
        grid = scan_table_grid(table_path)
        info["grid"] = {k: v for k, v in grid.items() if k not in ("w_values", "q2_values")}
    else:
        info["note"] = (
            "Table file is missing from the work directory — the Fortran will fail to open it. "
            f"Expected at {table_path}."
        )
    return info
