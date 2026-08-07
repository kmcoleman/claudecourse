"""Sub-tasks 8-12 checkpoint — the learner's ledger and first findings.

Sub-tasks 8-12 (Theme B) ask the learner to produce four artifacts at the
repository root:

    identities.csv   one row per entitlements account_id, resolved to an
                     employee_id where the match is unambiguous
    ledger.csv       de-duplicated entitlement grants with identity attached
    findings.json    SoD conflicts, validated against the findings contract
    exemptions.json  conflicts suppressed under ACP-4.2, kept for audit

Numbers below come from the shipped seed-locked 2026-Q3 export, so they are
exact rather than approximate. If none of the artifacts exist yet the whole
module skips — a fresh clone stays green.
"""

import csv
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "2026-Q3"
SCHEMA = json.load(
    open(ROOT / "src" / "meridian_capstone" / "contract" / "findings.schema.json")
)

IDENTITIES = ROOT / "identities.csv"
LEDGER = ROOT / "ledger.csv"
FINDINGS = ROOT / "findings.json"
EXEMPTIONS = ROOT / "exemptions.json"

ARTIFACTS = [IDENTITIES, LEDGER, FINDINGS, EXEMPTIONS]

if not any(p.exists() for p in ARTIFACTS):
    pytest.skip(
        "No Theme B artifacts found at the repository root. Work through "
        "sub-tasks 8-12 first — this module checks identities.csv, ledger.csv, findings.json "
        "and exemptions.json.",
        allow_module_level=True,
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _rows(path):
    if not path.exists():
        pytest.fail(f"{path.name} is missing — sub-tasks 8-12 expect it at the repo root.")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _json(path):
    if not path.exists():
        pytest.fail(f"{path.name} is missing — sub-tasks 8-12 expect it at the repo root.")
    return json.load(open(path))


def _col(row, *names):
    """Fetch the first column present, so column naming stays the learner's call."""
    for n in names:
        if n in row and row[n] is not None:
            return row[n].strip()
    pytest.fail(f"expected one of {names} among columns {sorted(row)}")


def _blank(v):
    return v in ("", None, "nan", "NaN")


def _source_accounts():
    with open(DATA / "entitlements.csv", newline="") as f:
        return {r["account_id"] for r in csv.DictReader(f)}


def _hr():
    with open(DATA / "hr_roster.csv", newline="") as f:
        return list(csv.DictReader(f))


SERVICE_ACCOUNT_NAMES = set(json.load(open(DATA / "service_accounts.json")))
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --------------------------------------------------------------------------
# Sub-task 9 — the canonical identity table
# --------------------------------------------------------------------------

def test_identities_has_one_row_per_account():
    rows = _rows(IDENTITIES)
    ids = [_col(r, "account_id") for r in rows]
    assert len(ids) == 1200, f"expected 1200 accounts, got {len(ids)}"
    assert len(set(ids)) == 1200, "account_id must be unique in identities.csv"
    assert set(ids) == _source_accounts(), (
        "identities.csv must cover exactly the accounts in entitlements.csv — "
        "no account may be dropped"
    )


def test_resolved_employee_ids_exist_in_hr():
    known = {r["employee_id"] for r in _hr()}
    unknown = {
        _col(r, "employee_id", "canonical_id")
        for r in _rows(IDENTITIES)
        if not _blank(_col(r, "employee_id", "canonical_id"))
    } - known
    assert not unknown, f"identities.csv resolves to employee_ids not in HR: {sorted(unknown)}"


def test_at_least_the_baseline_accounts_resolve():
    resolved = sum(
        1
        for r in _rows(IDENTITIES)
        if not _blank(_col(r, "employee_id", "canonical_id"))
    )
    assert resolved >= 1055, (
        f"only {resolved} accounts resolved to a person; exact firstname.lastname "
        "matching alone reaches 1055"
    )


def test_service_accounts_are_not_matched_to_a_person():
    for r in _rows(IDENTITIES):
        if _col(r, "account_name") in SERVICE_ACCOUNT_NAMES:
            assert _blank(_col(r, "employee_id", "canonical_id")), (
                f"{_col(r, 'account_name')} is a service account "
                "(data/2026-Q3/service_accounts.json) and has no human owner"
            )


def test_colliding_account_names_do_not_silently_merge():
    """jacob.miller is two different employees who each own an account."""
    by_id = {_col(r, "account_id"): r for r in _rows(IDENTITIES)}
    a, b = by_id.get("A000450"), by_id.get("A001148")
    assert a and b, "A000450 and A001148 must both appear in identities.csv"
    ea = _col(a, "employee_id", "canonical_id")
    eb = _col(b, "employee_id", "canonical_id")
    assert _blank(ea) or _blank(eb) or ea != eb, (
        "A000450 and A001148 are both named jacob.miller but belong to two "
        "different employees — they must not collapse onto one identity"
    )


# --------------------------------------------------------------------------
# Sub-task 10 — the ledger
# --------------------------------------------------------------------------

def test_ledger_is_deduplicated():
    rows = _rows(LEDGER)
    assert len(rows) == 15158, (
        f"expected 15158 ledger rows, got {len(rows)}. 15188 means nothing was "
        "de-duplicated; 15178 means you de-duplicated before normalising "
        "granted_date and 20 format-twins survived."
    )
    keys = [(_col(r, "account_id"), _col(r, "app"), _col(r, "role")) for r in rows]
    assert len(set(keys)) == len(keys), "ledger has duplicate (account_id, app, role) rows"


def test_ledger_dates_are_normalised():
    bad = [
        _col(r, "granted_date")
        for r in _rows(LEDGER)
        if not ISO.match(_col(r, "granted_date"))
    ]
    assert not bad, f"granted_date still holds non-ISO values, e.g. {bad[:3]}"


def test_jessica_schultz_collapses_to_one_identity():
    rows = [r for r in _rows(LEDGER) if _col(r, "account_id") == "A000323"]
    assert len(rows) == 11, f"A000323 should hold 11 distinct grants, got {len(rows)}"
    box = [r for r in rows if _col(r, "app") == "Box" and _col(r, "role") == "Member"]
    assert len(box) == 1, "the Box/Member grant for A000323 was recorded twice — collapse it"


def test_every_ledger_account_appears_in_identities():
    known = {_col(r, "account_id") for r in _rows(IDENTITIES)}
    missing = {_col(r, "account_id") for r in _rows(LEDGER)} - known
    assert not missing, f"ledger references accounts absent from identities.csv: {sorted(missing)[:5]}"


# --------------------------------------------------------------------------
# Sub-tasks 11-12 — findings
# --------------------------------------------------------------------------

def test_findings_match_the_contract():
    jsonschema.validate(_json(FINDINGS), SCHEMA)


def test_findings_are_the_two_real_sod_conflicts():
    sod = [f for f in _json(FINDINGS) if f["category"] == "sod_conflict"]
    got = sorted(f["account_id"] for f in sod)
    assert got == ["A000384", "A001115"], (
        f"expected SoD conflicts on A000384 and A001115, got {got}"
    )
    for f in sod:
        assert f["app"] == "Atlas ERP"
        assert f["severity"] == "critical", "the SoD matrix rates this pair critical"
        assert f["evidence"], "a finding a reviewer cannot trace is not a finding"


def test_controllers_are_exempt_not_reported():
    controllers = {"A000387", "A000674", "A001125"}
    reported = {f.get("account_id") for f in _json(FINDINGS)} & controllers
    assert not reported, (
        f"{sorted(reported)} hold AP Manager + Vendor Admin under the standing "
        "ACP-4.2 exemption — reporting them is a false positive"
    )


def test_exemptions_are_recorded_rather_than_dropped():
    exempt = _json(EXEMPTIONS)
    ids = sorted(e["account_id"] for e in exempt)
    assert ids == ["A000387", "A000674", "A001125"], (
        f"expected the three exempted Controllers, got {ids}"
    )
    for e in exempt:
        cites = e.get("policy_citations") or [e.get("clause", "")]
        assert any("ACP-4.2" in c for c in cites), (
            "each suppressed conflict must name the clause that suppressed it"
        )
