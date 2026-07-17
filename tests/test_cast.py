from datetime import date
from collections import Counter
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.cast import assign_narratives, PLANTED_PLAN
from meridian.narratives import NARRATIVES


def test_planted_counts_hit_targets():
    w = load_world("world")
    rng = make_rng(21)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    pairs = assign_narratives(pop, rng)
    counts = Counter(name for _, name in pairs)
    by_class = Counter()
    for name, n in counts.items():
        by_class[NARRATIVES[name].finding_class] += n
    assert by_class["must_catch"] == 24
    assert by_class["trap"] == 12
    # account-scoped judgment (coverage-gap judgments added elsewhere)
    assert by_class["judgment"] == 7


def test_everyone_assigned_once():
    w = load_world("world")
    rng = make_rng(21)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    pairs = assign_narratives(pop, rng)
    assert len(pairs) == len(pop)
    assert {p.employee_id for p, _ in pairs} == {p.employee_id for p in pop}


def test_planted_spread_across_departments():
    w = load_world("world")
    rng = make_rng(21)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    pairs = assign_narratives(pop, rng)
    planted_depts = {p.department for p, name in pairs
                     if NARRATIVES[name].finding_class != "clean"}
    assert len(planted_depts) >= 4
