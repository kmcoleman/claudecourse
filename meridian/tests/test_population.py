from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population


def test_population_size_matches_headcount():
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    assert len(pop) == 1200


def test_ids_unique_and_zero_padded():
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    ids = [p.employee_id for p in pop]
    assert len(set(ids)) == 1200
    assert all(i.startswith("E") and len(i) == 6 for i in ids)


def test_hire_dates_before_quarter_end():
    w = load_world("world")
    rng = make_rng(7)
    qe = date(2026, 9, 30)
    pop = build_population(w, rng, make_faker(rng), qe)
    assert all(p.hire_date < qe for p in pop)


def test_contractors_exist_and_are_minority():
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    contractors = [p for p in pop if p.employment_type == "Contractor"]
    assert 0 < len(contractors) < 300


def test_account_name_set_and_some_mismatch():
    # The name-format mismatch hazard must survive into account_name, or it
    # never reaches the exported entitlements and the join hazard is lost.
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    assert all(p.account_name for p in pop)          # every person has an IAM name
    plain = lambda p: f"{p.full_name.split()[0].lower()}.{p.full_name.split()[-1].lower()}"
    mismatched = [p for p in pop if p.account_name != plain(p)]
    assert 40 < len(mismatched) < 240                # ~10% of 1200
