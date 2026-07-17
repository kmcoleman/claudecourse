import csv
import json
import os
from meridian.generate import generate


def test_generate_writes_all_artifacts(tmp_path):
    out = tmp_path / "2026-Q3"
    key = tmp_path / "answer_key.json"
    generate(20260715, "2026-Q3", str(out), str(key))
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv"]:
        assert (out / name).exists()
    assert (out / "policies" / "access-control-policy.md").exists()
    k = json.load(open(key))
    assert k["counts"]["must_catch"] == 24
    assert k["counts"]["trap"] == 13   # 12 account traps + 1 new-app trap
    assert k["counts"]["judgment"] == 9  # 7 account + 2 coverage-gap


def _load(out):
    hr = list(csv.DictReader(open(out / "hr_roster.csv")))
    ent = list(csv.DictReader(open(out / "entitlements.csv")))
    prior = list(csv.DictReader(open(out / "prior_review.csv")))
    return hr, ent, prior


def test_coherence_every_case_derivable(tmp_path):
    out = tmp_path / "2026-Q3"
    key_path = tmp_path / "answer_key.json"
    key = __import__("meridian.generate", fromlist=["generate"]).generate(
        20260715, "2026-Q3", str(out), str(key_path))
    hr, ent, prior = _load(out)
    hr_by_id = {r["employee_id"]: r for r in hr}
    ent_by_acct = {}
    for r in ent:
        ent_by_acct.setdefault(r["account_id"], []).append(r)
    prior_apps = {r["app"] for r in prior}

    omitted_apps = set()

    for case in key["cases"]:
        subj = case["subject"]
        if case["narrative"] == "TerminatedWithActiveAdmin" or \
           case["narrative"] == "TerminatedWithActiveAdminUniversal":
            # HR row shows a term date; the flagged entitlement still exists
            row = hr_by_id[subj["employee_id"]]
            assert row["term_date"] != "", "terminated case must have a term_date"
            assert subj["account_id"] in ent_by_acct
        elif case["narrative"] == "OrphanNoHRRecord":
            assert subj["employee_id"] in (None, "")
            assert subj["account_id"] in ent_by_acct   # entitlements exist, HR does not
        elif case["narrative"] == "PriorReviewCoverageGap":
            assert subj["app"] not in prior_apps       # genuinely absent from prior review
            omitted_apps.add(subj["app"])
        elif case["narrative"] == "NewAppNoPriorReview":
            assert subj["app"] not in prior_apps       # the trap: also absent, but expected
            omitted_apps.add(subj["app"])

    # Strengthened check: the new app AND both skipped apps must be genuinely
    # absent from the FINAL written prior_review.csv -- guards against the
    # coupling where narrative-supplied prior-review rows (e.g. the
    # ContractorOverstayWithVouch VPN row) are appended to prior_review
    # without being filtered against the omitted-apps set.
    assert len(omitted_apps) == 3, "expected 2 coverage-gap apps + 1 new app"
    for app in omitted_apps:
        assert app not in prior_apps, (
            f"{app!r} was supposed to be omitted from prior review, "
            "but appears in the final prior_review.csv"
        )
