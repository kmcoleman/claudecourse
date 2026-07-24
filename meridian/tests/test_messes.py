from datetime import date
from meridian.models import Entitlement, Person
from meridian.rng import make_rng
from meridian.messes import duplicate_some_accounts, drift_department_casing, format_grant_date


def _ent(aid):
    return Entitlement(aid, "a.b", "Slack", "Member", date(2025, 1, 1), "gw", None)


def test_duplicates_added():
    rows = [_ent(f"A{i}") for i in range(100)]
    out = duplicate_some_accounts(rows, make_rng(2))
    assert len(out) > len(rows)


def test_department_casing_drifts_for_some():
    people = [Person(f"E{i}", "A B", "a@b.com", "Finance & Accounting", "t",
                     date(2020, 1, 1), None, "FTE", "active", True) for i in range(100)]
    out = drift_department_casing(people, make_rng(2))
    assert any(p.department != "Finance & Accounting" for p in out)
    assert all(p.department.strip().lower() == "finance & accounting" for p in out)


def test_date_formats():
    assert format_grant_date(date(2026, 3, 4), "iso") == "2026-03-04"
    assert format_grant_date(date(2026, 3, 4), "us") == "03/04/2026"
