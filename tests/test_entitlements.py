from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.entitlements import baseline_entitlements


def test_everyone_has_universal_apps():
    w = load_world("world")
    rng = make_rng(3)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    p = build_population(w, rng, fake, qe)[0]
    ents = baseline_entitlements(p, w, rng, fake, qe, account_id="A000001")
    apps = {e.app for e in ents}
    assert {"Slack", "VPN", "Active Directory"} <= apps


def test_grant_dates_before_quarter_end():
    w = load_world("world")
    rng = make_rng(3)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    p = build_population(w, rng, fake, qe)[0]
    ents = baseline_entitlements(p, w, rng, fake, qe, account_id="A000001")
    assert all(e.granted_date < qe for e in ents)


def test_population_entitlement_total_in_range():
    w = load_world("world")
    rng = make_rng(3)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    pop = build_population(w, rng, fake, qe)
    total = sum(len(baseline_entitlements(p, w, rng, fake, qe, f"A{i:06d}"))
               for i, p in enumerate(pop))
    assert 12000 <= total <= 18000
