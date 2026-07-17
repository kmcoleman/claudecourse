from datetime import date, timedelta
from dataclasses import replace
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.must_catch import (
    TerminatedWithActiveAdmin, OrphanNoHRRecord, DormantPrivileged, GrantBeforeHireDate,
)


def _ctx(seed=9):
    w = load_world("world")
    rng = make_rng(seed)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_terminated_sets_term_date_and_keeps_admin():
    w, rng, fake, qe, person = _ctx()
    r = TerminatedWithActiveAdmin.emit(person, w, rng, fake, qe, "A000010")
    assert len(r.cases) == 1
    assert r.hr_rows[0].term_date is not None and r.hr_rows[0].term_date < qe
    assert r.hr_rows[0].status == "terminated"
    privileged = {ro for a in w.apps.values() for ro in a.privileged_roles}
    assert any(e.role in privileged for e in r.iam_rows)


def test_orphan_has_no_hr_row():
    w, rng, fake, qe, person = _ctx()
    r = OrphanNoHRRecord.emit(person, w, rng, fake, qe, "A000011")
    assert r.hr_rows == []
    assert r.iam_rows
    assert r.cases[0].subject.get("employee_id") in (None, "")


def test_dormant_last_login_exceeds_180_days():
    w, rng, fake, qe, person = _ctx()
    r = DormantPrivileged.emit(person, w, rng, fake, qe, "A000012")
    flagged = r.cases[0].subject["account_id"]
    ent = [e for e in r.iam_rows if e.account_id == flagged and e.last_login][0]
    assert (qe - ent.last_login).days > 180


def test_grant_before_hire_is_actually_before():
    w, rng, fake, qe, person = _ctx()
    r = GrantBeforeHireDate.emit(person, w, rng, fake, qe, "A000013")
    hire = r.hr_rows[0].hire_date
    bad = [e for e in r.iam_rows if e.granted_date < hire]
    assert bad, "expected an entitlement granted before hire date"
