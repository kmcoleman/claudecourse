from __future__ import annotations

from datetime import timedelta

from meridian.models import AppSelection, Entitlement, PriorReviewRow


def build_prior_review(iam_rows: list[Entitlement], selection: AppSelection,
                       narrative_rows: list[PriorReviewRow], rng, quarter_end) -> list[PriorReviewRow]:
    omit = {selection.new_app, *selection.skipped_apps}
    rows: list[PriorReviewRow] = []
    for e in iam_rows:
        if e.app in omit:
            continue
        if rng.random() < 0.5:                 # a plausible subset was reviewed
            rows.append(PriorReviewRow(
                account_id=e.account_id,
                app=e.app,
                reviewer="prior.reviewer",
                decision="approved",
                review_date=quarter_end - timedelta(days=rng.randint(80, 100)),
            ))
    rows.extend(narrative_rows)
    return rows
