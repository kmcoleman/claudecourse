"""The frozen capstone contract. The instructor's grader imports run_review and
calls it as run_review(export_dir, limit=None). Keep this signature exact.

You implement the body across Modules 1-6. It must return a list of findings,
each conforming to contract/findings.schema.json. `limit` caps how many
candidates reach the agent layer, for cheap iteration; None means the full run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_review(export_dir: Path, limit: int | None = None) -> list[dict]:
    export_dir = Path(export_dir)
    # TODO(you): build the Ledger, the agents, and the evidence writer here.
    # Return findings conforming to contract/findings.schema.json.
    return []


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="meridian_capstone.contract.run_review")
    ap.add_argument("export_dir")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    findings = run_review(Path(args.export_dir), limit=args.limit)
    json.dump(findings, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
