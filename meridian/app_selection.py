from __future__ import annotations

from datetime import date, timedelta

from meridian.models import AppSelection, Case, World


def choose_apps(world: World, rng) -> AppSelection:
    new_candidates = sorted(n for n, a in world.apps.items()
                            if a.tier in {"business", "infra"})
    new_app = rng.choice(new_candidates)
    skip_candidates = sorted(n for n, a in world.apps.items()
                             if a.tier == "business" and n != new_app)
    skipped = rng.sample(skip_candidates, 2)
    return AppSelection(new_app=new_app, skipped_apps=sorted(skipped))


def effective_impl_date(app_name: str, selection: AppSelection, world: World,
                        quarter_start: date) -> date:
    if app_name == selection.new_app:
        return quarter_start + timedelta(days=20)
    return world.apps[app_name].implementation_date


def coverage_gap_cases(selection: AppSelection) -> list[Case]:
    cases = []
    for app in selection.skipped_apps:
        cases.append(Case(f"case-gap-{app}", "PriorReviewCoverageGap", "judgment",
                          "application", {"app": app},
                          {"category": "coverage_gap", "recommendation": "review"},
                          ["not_in_prior_review", "implementation_date"]))
    cases.append(Case(f"case-newapp-{selection.new_app}", "NewAppNoPriorReview", "trap",
                      "application", {"app": selection.new_app}, {}, []))
    return cases
