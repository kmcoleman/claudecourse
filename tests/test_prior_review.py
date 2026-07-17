from datetime import date, timedelta
from meridian.models import Entitlement, AppSelection
from meridian.rng import make_rng
from meridian.prior_review import build_prior_review


def _ent(app, aid):
    return Entitlement(aid, "x.y", app, "User", date(2025, 1, 1), "gw", date(2026, 9, 1))


def test_skipped_and_new_apps_absent():
    rows = [_ent("Box", "A1"), _ent("Expense", "A2"), _ent("Slack", "A3"),
            _ent("Snowflake", "A4")]
    sel = AppSelection(new_app="Snowflake", skipped_apps=["Box", "Expense"])
    pr = build_prior_review(rows, sel, [], make_rng(1), date(2026, 9, 30))
    covered = {r.app for r in pr}
    assert "Snowflake" not in covered
    assert "Box" not in covered and "Expense" not in covered
    assert "Slack" in covered


def test_narrative_rows_appended():
    from meridian.models import PriorReviewRow
    rows = [_ent("Slack", "A3")]
    sel = AppSelection(new_app="Snowflake", skipped_apps=["Box", "Expense"])
    nar = [PriorReviewRow("A9", "VPN", "prior.reviewer", "conditional", date(2026, 6, 1))]
    pr = build_prior_review(rows, sel, nar, make_rng(1), date(2026, 9, 30))
    assert any(r.decision == "conditional" for r in pr)
