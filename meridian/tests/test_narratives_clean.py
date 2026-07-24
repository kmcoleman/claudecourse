from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.clean import CleanFTE, CleanPrivileged


def _ctx():
    w = load_world("world")
    rng = make_rng(5)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_clean_fte_has_no_cases():
    w, rng, fake, qe, person = _ctx()
    r = CleanFTE.emit(person, w, rng, fake, qe, "A000001")
    assert r.cases == []
    assert r.hr_rows == [person]


def test_clean_privileged_has_ticket_and_no_cases():
    w, rng, fake, qe, person = _ctx()
    r = CleanPrivileged.emit(person, w, rng, fake, qe, "A000002")
    assert r.cases == []
    priv = [e for e in r.iam_rows if e.role in
            {ro for a in w.apps.values() for ro in a.privileged_roles}]
    assert priv, "expected at least one privileged entitlement"
    assert r.tickets, "privileged grant must have an approval ticket"
