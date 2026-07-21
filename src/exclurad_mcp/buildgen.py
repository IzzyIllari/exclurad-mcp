"""One-source build generation for EXCLURAD's channel-specific hardcodes.

The eta and pion configurations differ in exactly 15 localized regions across
exclurad.F and mpintp.inc (verified by diffing IzzyIllari/exclurad against
JeffersonLab/exclurad; fint.F and spp.inc are identical). Instead of
maintaining two diverging copies, this module keeps ONE template per file with
named slot markers, plus a registry (slots.json) recording, for every slot:
what it means, which values are currently accepted, and the exact source text
per channel.

Correctness contract: generating 'eta' must reproduce the fork's files
byte-for-byte, and 'pion' must reproduce upstream's — verify_against() checks
exactly that. A slot value is "accepted" precisely because it round-trips to a
validated source.

Template format: a slot is a single line `*@@SLOT <name>@@` (a Fortran comment,
so a template is still syntax-highlightable); generation replaces the marker
line with the channel's lines from slots.json.
"""

import difflib
import json
import re
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "templates"
MARKER_RE = re.compile(r"^\*@@SLOT (?P<name>[a-z0-9_]+)@@$")

TEMPLATED_FILES = ("exclurad.F", "mpintp.inc")
IDENTICAL_FILES = ("fint.F", "spp.inc")  # same in both channels; copied verbatim


def weave(base_lines: list[str], other_lines: list[str]) -> list[tuple]:
    """Diff two line lists into segments: ('common', lines) or
    ('slot', base_lines, other_lines)."""
    sm = difflib.SequenceMatcher(a=base_lines, b=other_lines, autojunk=False)
    segments = []
    for tag, a0, a1, b0, b1 in sm.get_opcodes():
        if tag == "equal":
            segments.append(("common", base_lines[a0:a1]))
        else:
            segments.append(("slot", base_lines[a0:a1], other_lines[b0:b1]))
    return segments


def build_template(
    eta_text: str, pion_text: str, annotations: list[dict]
) -> tuple[str, list[dict]]:
    """Produce (template_text, slots) from the two channel sources.

    annotations: one dict per expected slot, in file order:
      {"name", "description", "accepted_values": {channel: explanation}}
    Raises if the number of differing regions does not match — that means the
    sources changed and the annotations need reviewing, which is the point.
    """
    eta_lines = eta_text.splitlines(keepends=True)
    pion_lines = pion_text.splitlines(keepends=True)
    segments = weave(eta_lines, pion_lines)
    n_slots = sum(1 for s in segments if s[0] == "slot")
    if n_slots != len(annotations):
        raise ValueError(
            f"Source has {n_slots} differing regions but {len(annotations)} "
            "annotations were provided; re-diff and update the annotations."
        )
    out_lines: list[str] = []
    slots: list[dict] = []
    it = iter(annotations)
    for seg in segments:
        if seg[0] == "common":
            out_lines.extend(seg[1])
        else:
            ann = next(it)
            out_lines.append(f"*@@SLOT {ann['name']}@@\n")
            slots.append(
                {
                    "name": ann["name"],
                    "description": ann["description"],
                    "accepted_values": ann.get("accepted_values", {}),
                    "text": {"eta": seg[1], "pion": seg[2]},
                }
            )
    return "".join(out_lines), slots


def _load(template_dir: Path | None = None) -> tuple[dict, dict]:
    tdir = Path(template_dir) if template_dir else TEMPLATE_DIR
    registry = json.loads((tdir / "slots.json").read_text())
    templates = {f: (tdir / f"{f}.template").read_text() for f in registry["files"]}
    return registry, templates


def list_slots(template_dir: Path | None = None) -> list[dict]:
    """All slots with descriptions and currently-accepted values per channel."""
    registry, _ = _load(template_dir)
    out = []
    for fname, slots in registry["slots"].items():
        for s in slots:
            out.append(
                {
                    "file": fname,
                    "name": s["name"],
                    "description": s["description"],
                    "accepted_values": s["accepted_values"],
                    "channels": sorted(s["text"].keys()),
                }
            )
    return out


def generate_source(channel: str, template_dir: Path | None = None) -> dict[str, str]:
    """Render every templated file for a channel. Returns {filename: text}."""
    registry, templates = _load(template_dir)
    rendered: dict[str, str] = {}
    for fname, template in templates.items():
        slot_map = {s["name"]: s for s in registry["slots"][fname]}
        out_lines = []
        for line in template.splitlines(keepends=True):
            m = MARKER_RE.match(line.rstrip("\n"))
            if m:
                slot = slot_map[m.group("name")]
                if channel not in slot["text"]:
                    raise ValueError(
                        f"Slot '{slot['name']}' has no value for channel "
                        f"'{channel}'; accepted: {sorted(slot['text'])}"
                    )
                out_lines.extend(slot["text"][channel])
            else:
                out_lines.append(line)
        rendered[fname] = "".join(out_lines)
    return rendered


def write_build(channel: str, dest_dir: str | Path,
                template_dir: Path | None = None) -> dict:
    """Write the rendered sources for a channel into dest_dir."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    rendered = generate_source(channel, template_dir)
    written = []
    for fname, text in rendered.items():
        (dest / fname).write_text(text)
        written.append(str(dest / fname))
    return {"channel": channel, "written": written,
            "note": f"Also copy the channel's lookup table and the shared files "
                    f"{IDENTICAL_FILES} + Makefile into {dest}, then run make."}


def verify_against(channel: str, reference_dir: str | Path,
                   template_dir: Path | None = None) -> dict:
    """Byte-identity check of generated sources against a validated checkout."""
    ref = Path(reference_dir)
    rendered = generate_source(channel, template_dir)
    results = {}
    for fname, text in rendered.items():
        ref_file = ref / fname
        if not ref_file.exists():
            results[fname] = "MISSING_REFERENCE"
            continue
        results[fname] = "IDENTICAL" if ref_file.read_text() == text else "DIFFERS"
    ok = all(v == "IDENTICAL" for v in results.values())
    return {"channel": channel, "reference": str(ref), "files": results,
            "verdict": "PASS" if ok else "FAIL"}
