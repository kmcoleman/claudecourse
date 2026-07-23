from __future__ import annotations

import argparse
import os

from meridian.generate import generate


def kit_export(seed: int, quarter: str, kit_dir: str) -> None:
    """Generate a quarter's data into the kit, WITHOUT the answer key."""
    out_dir = os.path.join(kit_dir, "data", quarter)
    generate(seed, quarter, out_dir, key_path=None)  # key intentionally omitted


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="meridian.kit_export")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--quarter", required=True)
    ap.add_argument("--kit-dir", required=True)
    args = ap.parse_args(argv)
    kit_export(args.seed, args.quarter, args.kit_dir)


if __name__ == "__main__":
    main()
