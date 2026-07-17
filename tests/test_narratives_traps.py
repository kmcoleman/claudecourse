from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.traps import (
    ApprovedServiceAccount, BreakGlassDormant, EmployeeOnLeave, ExemptedSoDPair,
)


def _ctx(seed=13):
    w = load_world("world")
    rng = make_rng(seed)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_traps_have_empty_expected():
    w, rng, fake, qe, person = _ctx()
    for i, narr in enumerate([ApprovedServiceAccount, BreakGlassDormant,
                              EmployeeOnLeave, ExemptedSoDPair]):
        r = narr.emit(person, w, rng, fake, qe, f"A0000{i}0")
        assert r.cases[0].finding_class == "trap"
        assert r.cases[0].expected == {}


def test_on_leave_not_terminated():
    w, rng, fake, qe, person = _ctx()
    r = EmployeeOnLeave.emit(person, w, rng, fake, qe, "A000030")
    assert r.hr_rows[0].status == "on_leave"
    assert r.hr_rows[0].term_date is None


def test_service_account_name_in_registry():
    w, rng, fake, qe, person = _ctx()
    r = ApprovedServiceAccount.emit(person, w, rng, fake, qe, "A000031")
    assert any(e.account_name in w.service_accounts for e in r.iam_rows)


def test_exempted_controller_holds_only_the_exempted_pair():
    # The Controller trap must carry ONLY the exempted Vendor Admin+AP Manager pair on
    # Atlas — never a baseline AP Clerk/GL Accountant, which would form a genuine
    # NON-exempt SoD conflict and make this "don't flag" trap actually flaggable.
    for seed in range(41):
        w = load_world("world")
        rng = make_rng(seed)
        fake = make_faker(rng)
        qe = date(2026, 9, 30)
        person = build_population(w, rng, fake, qe)[0]
        r = ExemptedSoDPair.emit(person, w, rng, fake, qe, "A000040")
        atlas_roles = sorted(e.role for e in r.iam_rows if e.app == "Atlas ERP")
        assert atlas_roles == ["AP Manager", "Vendor Admin"], f"seed {seed}: {atlas_roles}"
        pairs = [(e.app, e.role) for e in r.iam_rows]
        assert len(pairs) == len(set(pairs)), f"seed {seed}: duplicate rows"
