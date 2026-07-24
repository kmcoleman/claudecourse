#!/usr/bin/env python3
"""Build the course portal (index.html) from its template.

The portal is a single, dependency-free HTML file that ships at the repo root as
the student's landing page. To keep it usable by double-clicking (file://) while
staying small, the *small* world files are embedded directly into the page and
the two *large* tables (entitlements, prior_review) are fetched on demand.

This script reads ``scripts/portal.template.html``, fills every
``<script data-embed="<quarter>/<path>"></script>`` slot with the contents of the
matching file under ``data/``, and writes ``index.html`` at the repo root.

Re-run it whenever the embedded data or the template changes::

    python scripts/build_portal.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts" / "portal.template.html"
OUTPUT = ROOT / "index.html"
DATA = ROOT / "data"

# Matches: <script ... data-embed="2026-Q3/hr_roster.csv" ...></script>
SLOT = re.compile(r'(<script\b[^>]*\bdata-embed="([^"]+)"[^>]*>)(\s*)(</script>)')


def inject(match: re.Match) -> str:
    open_tag, rel_path, _ws, close_tag = match.groups()
    src = DATA / rel_path
    if not src.exists():
        raise SystemExit(f"error: embed source not found: {src}")
    text = src.read_text(encoding="utf-8")
    # A closing </script> inside embedded text would end the tag early. None of the
    # world data contains it, but guard anyway so this stays correct if data changes.
    text = text.replace("</script", "<\\/script")
    return f"{open_tag}\n{text}\n{close_tag}"


def main() -> int:
    if not TEMPLATE.exists():
        raise SystemExit(f"error: template not found: {TEMPLATE}")

    html = TEMPLATE.read_text(encoding="utf-8")
    slots = SLOT.findall(html)
    if not slots:
        raise SystemExit("error: no data-embed slots found in template")

    html = SLOT.sub(inject, html)
    OUTPUT.write_text(html, encoding="utf-8")

    kb = OUTPUT.stat().st_size / 1024
    print(f"wrote {OUTPUT.relative_to(ROOT)}  ({kb:.0f} KB, {len(slots)} embeds)")
    for _open, rel, _ws, _close in slots:
        print(f"  embedded  {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
