from datetime import date

from meridian.models import Person, Entitlement, Case, EmitResult


def test_person_is_frozen_and_replaceable():
    from dataclasses import replace
    p = Person("E1", "Bob Smith", "bob@x.com", "Finance", "Clerk",
               date(2020, 1, 1), None, "FTE", "active", True)
    p2 = replace(p, status="terminated", term_date=date(2026, 3, 1))
    assert p.status == "active" and p2.status == "terminated"


def test_emit_result_defaults_empty():
    r = EmitResult(hr_rows=[], iam_rows=[], tickets=[], prior_review_rows=[], cases=[])
    assert r.cases == []


def test_case_holds_scope_and_expected():
    c = Case("c1", "TerminatedWithActiveAdmin", "must_catch", "account",
             {"account_id": "A1"}, {"recommendation": "revoke"}, ["term_date"])
    assert c.scope == "account" and c.expected["recommendation"] == "revoke"
