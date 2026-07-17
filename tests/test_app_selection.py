from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng
from meridian.app_selection import (_RESERVED_FOR_NARRATIVES, choose_apps,
                                    coverage_gap_cases, effective_impl_date)


def test_selection_disjoint_and_correct_tiers():
    w = load_world("world")
    sel = choose_apps(w, make_rng(4))
    assert sel.new_app not in sel.skipped_apps
    assert len(set(sel.skipped_apps)) == 2
    assert w.apps[sel.new_app].tier in {"business", "infra"}
    for a in sel.skipped_apps:
        assert w.apps[a].tier == "business"


def test_new_app_impl_date_inside_quarter():
    w = load_world("world")
    sel = choose_apps(w, make_rng(4))
    qs = date(2026, 7, 1)
    d = effective_impl_date(sel.new_app, sel, w, qs)
    assert d >= qs


def test_coverage_gap_cases_shape():
    w = load_world("world")
    sel = choose_apps(w, make_rng(4))
    cases = coverage_gap_cases(sel)
    gaps = [c for c in cases if c.expected]
    traps = [c for c in cases if not c.expected]
    assert len(gaps) == 2 and len(traps) == 1
    assert all(c.scope == "application" for c in cases)


def test_new_app_never_a_planted_narrative_app():
    # The per-seed new_app triggers a "fresh rollout" date override in generate.py
    # that rewrites every grant on that app. Planted narratives place findings by
    # setting specific grant dates on GitHub Enterprise / AWS Prod / Helix ITSM;
    # if new_app ever coincided, the override would destroy those findings. Across
    # many seeds, new_app must never land on a planted-narrative app.
    w = load_world("world")
    for seed in range(40):
        sel = choose_apps(w, make_rng(seed))
        assert sel.new_app not in _RESERVED_FOR_NARRATIVES, (
            f"seed {seed}: new_app {sel.new_app!r} is a reserved planted-narrative app"
        )


def test_selection_is_seed_varied():
    w = load_world("world")
    s1 = choose_apps(w, make_rng(1))
    s2 = choose_apps(w, make_rng(99))
    assert (s1.new_app, s1.skipped_apps) != (s2.new_app, s2.skipped_apps)
