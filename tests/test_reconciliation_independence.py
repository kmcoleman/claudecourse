"""Guard: account_id numbering is independent of employee_id numbering.

The generator once walked employees and accounts in the same order, so
``account_id`` digits equalled ``employee_id`` digits for the same person
(A000019 <-> E00019). That let a learner shortcut the whole reconciliation
lesson by extracting digits instead of resolving names. The account numbers are
now drawn from an independently shuffled sequence, so the digits no longer line
up. This test fails loudly if that regression ever comes back.

It runs against the shipped, seed-locked exports and needs no learner artifacts.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "2026-Q3"

if not (DATA / "entitlements.csv").exists() or not (DATA / "hr_roster.csv").exists():
    pytest.skip(
        "data/2026-Q3 export is missing — generate it before running this guard.",
        allow_module_level=True,
    )


def _digits(ident):
    """Strip the letter prefix and leading zeros: A000019 -> '19', E00019 -> '19'."""
    return ident[1:].lstrip("0")


def _name_key(full_name):
    parts = [p for p in full_name.split() if p.isalpha()]
    if len(parts) < 2:
        return None
    return f"{parts[0].lower()}.{parts[-1].lower()}"


def _reconcile():
    """Name-based resolution: {account_id: employee_id} for unambiguous matches."""
    ent = list(csv.DictReader(open(DATA / "entitlements.csv", newline="")))
    hr = list(csv.DictReader(open(DATA / "hr_roster.csv", newline="")))

    name_by_acct = {}
    for r in ent:
        name_by_acct.setdefault(r["account_id"], r["account_name"])

    emps_by_key = defaultdict(list)
    for p in hr:
        k = _name_key(p["full_name"])
        if k:
            emps_by_key[k].append(p["employee_id"])

    resolved = {}
    for acct, name in name_by_acct.items():
        emps = set(emps_by_key.get(name, []))
        if len(emps) == 1:
            resolved[acct] = next(iter(emps))
    return resolved


def test_account_and_employee_ids_are_digit_independent():
    """The digit shortcut must be broken: matched account/employee ids rarely align.

    Under the old sequential-walk leak, every one of the ~1055 name-matched
    accounts had account_id digits equal to its employee_id digits. With
    independent numbering only a handful can coincide by chance, so anything
    beyond a tiny fraction means the leak is back.
    """
    resolved = _reconcile()
    assert resolved, "reconciliation resolved nothing — export looks wrong"

    coincidences = [
        (acct, emp)
        for acct, emp in resolved.items()
        if _digits(acct) == _digits(emp)
    ]
    matched = len(resolved)
    # A leak makes ~all matched pairs coincide; independence leaves ~0-2 by chance.
    assert len(coincidences) <= max(5, matched // 200), (
        f"{len(coincidences)} of {matched} name-matched accounts share their "
        f"digits with the employee they resolve to (e.g. {coincidences[:5]}). "
        "account_id must be numbered independently of employee_id — the "
        "reconciliation shortcut has regressed."
    )
