import csv
from pathlib import Path
from meridian_capstone.mcp_server import server as srv

DATA = Path(__file__).resolve().parent.parent / "data" / "2026-Q3"


def _any_employee_id():
    return next(csv.DictReader(open(DATA / "hr_roster.csv")))["employee_id"]


def _any_account_id():
    return next(csv.DictReader(open(DATA / "entitlements.csv")))["account_id"]


def test_get_employee_known_and_unknown():
    emp = _any_employee_id()
    rec = srv._get_employee(DATA, emp)
    assert rec is not None and rec["employee_id"] == emp
    assert srv._get_employee(DATA, "E999999") is None


def test_get_account_returns_entitlements():
    acct = _any_account_id()
    rec = srv._get_account(DATA, acct)
    assert rec is not None
    assert rec["account_id"] == acct
    assert isinstance(rec["entitlements"], list) and rec["entitlements"]


def test_get_application_has_implementation_date():
    app = srv._get_application(DATA, "Atlas ERP")
    assert app is not None and "implementation_date" in app
    assert srv._get_application(DATA, "Nonexistent App") is None


def test_service_account_registry_check():
    assert srv._is_approved_service_account(DATA, "marcus.pipeline") is True
    assert srv._is_approved_service_account(DATA, "definitely.not.a.svc") is False


def test_sod_matrix_has_conflicts_and_exemption():
    m = srv._get_sod_matrix(DATA)
    assert m["conflicts"] and any(e.get("clause") == "ACP-4.2" for e in m["exemptions"])


def test_search_tickets_by_account():
    # find an account that actually has a ticket
    import json
    tickets = json.load(open(DATA / "access_tickets.json"))
    if tickets:
        acct = tickets[0]["account_id"]
        found = srv._search_tickets(DATA, acct)
        assert any(t["account_id"] == acct for t in found)
