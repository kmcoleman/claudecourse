"""Offline green light: data + contract + MCP. Free, deterministic, CI-able.
Run with `pytest -m "not api"` to skip the paid API check in test_api.py."""
import json
from pathlib import Path

import jsonschema

from meridian_capstone.contract.run_review import run_review
from meridian_capstone.mcp_server import server as srv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "2026-Q3"
SCHEMA = json.load(open(ROOT / "src" / "meridian_capstone" / "contract" / "findings.schema.json"))


def test_data_directory_is_complete():
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv", "applications.json", "sod_matrix.json",
                 "service_accounts.json"]:
        assert (DATA / name).exists(), name


def test_contract_runs_and_validates():
    findings = run_review(DATA)
    assert isinstance(findings, list)
    jsonschema.validate(findings, SCHEMA)
    jsonschema.validate(json.load(open(ROOT / "examples" / "sample_findings.json")), SCHEMA)


def test_mcp_tools_answer():
    apps = srv._get_application(DATA, "Atlas ERP")
    assert apps and "implementation_date" in apps
    import csv
    emp = next(csv.DictReader(open(DATA / "hr_roster.csv")))["employee_id"]
    assert srv._get_employee(DATA, emp) is not None
