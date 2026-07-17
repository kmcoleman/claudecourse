from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.judgment import (
    ContractorOverstayWithVouch, TransferKeptOldAccess, SoDConflictWithCompensatingControl,
)


def _ctx(seed=11):
    w = load_world("world")
    rng = make_rng(seed)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_contractor_overstay_has_vouch_ticket_and_conditional_prior():
    w, rng, fake, qe, person = _ctx()
    r = ContractorOverstayWithVouch.emit(person, w, rng, fake, qe, "A000020")
    assert r.cases[0].finding_class == "judgment"
    assert r.cases[0].expected["recommendation"] == "review"
    assert r.tickets, "expected a vouch ticket"
    assert any(pr.decision == "conditional" for pr in r.prior_review_rows)


def test_sod_conflict_holds_both_roles():
    w, rng, fake, qe, person = _ctx()
    r = SoDConflictWithCompensatingControl.emit(person, w, rng, fake, qe, "A000021")
    roles = {e.role for e in r.iam_rows if e.app == "Atlas ERP"}
    assert {"Vendor Admin", "AP Manager"} <= roles


def test_sod_account_atlas_roles_are_exactly_the_pair():
    # Regression test: baseline_entitlements can grant a Finance person a
    # random non-privileged Atlas ERP role (AP Clerk, AP Manager, GL
    # Accountant) BEFORE the narrative appends its own Vendor Admin +
    # AP Manager roles. That leak either creates a second, uncataloged SoD
    # conflict (AP Clerk + AP Manager) or a duplicate (Atlas ERP, AP Manager)
    # row. The narrative must fully own this account's Atlas ERP access.
    for seed in range(41):
        w = load_world("world")
        rng = make_rng(seed)
        fake = make_faker(rng)
        qe = date(2026, 9, 30)
        person = build_population(w, rng, fake, qe)[0]
        r = SoDConflictWithCompensatingControl.emit(person, w, rng, fake, qe, "A000021")

        atlas_roles = [e.role for e in r.iam_rows if e.app == "Atlas ERP"]
        assert set(atlas_roles) == {"Vendor Admin", "AP Manager"}, (
            f"seed={seed}: unexpected Atlas ERP roles {atlas_roles}"
        )

        pairs = [(e.app, e.role) for e in r.iam_rows]
        assert len(pairs) == len(set(pairs)), (
            f"seed={seed}: duplicate (app, role) rows on account: {pairs}"
        )
