import csv
import json
from datetime import datetime

import pytest

from meridian.generate import generate, quarter_bounds
from meridian.world import load_world


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
    tickets = json.load(open(out / "access_tickets.json"))
    return hr, ent, prior, tickets


def parse_date(s):
    """Entitlements CSV deliberately mixes ISO (YYYY-MM-DD) and US (MM/DD/YYYY)
    date formats per row. HR roster dates are always ISO, which this also parses
    fine since ISO is tried first. Blank strings return None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def test_coherence_every_case_derivable(tmp_path):
    out = tmp_path / "2026-Q3"
    key_path = tmp_path / "answer_key.json"
    key = generate(20260715, "2026-Q3", str(out), str(key_path))
    hr, ent, prior, tickets = _load(out)
    w = load_world("world")
    quarter_end = quarter_bounds("2026-Q3")[1]

    hr_by_id = {r["employee_id"]: r for r in hr}
    ent_by_acct = {}
    for r in ent:
        ent_by_acct.setdefault(r["account_id"], []).append(r)
    prior_apps = {r["app"] for r in prior}

    omitted_apps = set()

    for case in key["cases"]:
        subj = case["subject"]
        narrative = case["narrative"]

        if narrative in ("TerminatedWithActiveAdmin", "TerminatedWithActiveAdminUniversal"):
            # HR row shows a term date; the flagged entitlement still exists
            row = hr_by_id[subj["employee_id"]]
            assert row["term_date"] != "", "terminated case must have a term_date"
            assert subj["account_id"] in ent_by_acct
            rows_acct = ent_by_acct[subj["account_id"]]
            assert any(r["app"] == subj["app"] and r["role"] == subj["entitlement"]
                       for r in rows_acct), "flagged privileged grant not found on account"

        elif narrative == "OrphanNoHRRecord":
            assert subj["employee_id"] in (None, "")
            assert subj["account_id"] in ent_by_acct   # entitlements exist, HR does not

        elif narrative == "PrivilegedGrantNoTicket":
            role = subj["entitlement"]
            app = subj["app"]
            assert role in w.apps[app].privileged_roles, (
                f"{role!r} is not a privileged role for {app!r}"
            )
            matching_tickets = [t for t in tickets
                                if t["account_id"] == subj["account_id"]
                                and t["app"] == app and t["role"] == role]
            assert not matching_tickets, "ticket exists for a supposedly ticket-less grant"

        elif narrative == "GrantBeforeHireDate":
            row = hr_by_id[subj["employee_id"]]
            hire_date = parse_date(row["hire_date"])
            assert hire_date is not None
            rows_acct = ent_by_acct[subj["account_id"]]
            flagged = [r for r in rows_acct
                      if r["app"] == subj["app"] and r["role"] == subj["entitlement"]]
            assert flagged, "flagged entitlement row missing from account"
            assert any(parse_date(r["granted_date"]) is not None
                       and parse_date(r["granted_date"]) < hire_date
                       for r in flagged), "no grant on this account predates the hire date"

        elif narrative == "DormantPrivileged":
            rows_acct = ent_by_acct[subj["account_id"]]
            assert rows_acct
            for r in rows_acct:
                ll = parse_date(r["last_login"])
                assert ll is None or (quarter_end - ll).days > 180, (
                    f"account {subj['account_id']} has a non-dormant entitlement row"
                )

        elif narrative == "ContractorOverstayWithVouch":
            row = hr_by_id[subj["employee_id"]]
            assert row["employment_type"] == "Contractor"
            assert row["status"] == "active"
            term_date = parse_date(row["term_date"])
            assert term_date is not None and term_date < quarter_end
            rows_acct = ent_by_acct[subj["account_id"]]
            assert any(r["app"] == subj["app"] and r["role"] == subj["entitlement"]
                       for r in rows_acct), (
                "flagged entitlement (VPN / User) not found on the contractor's account"
            )
            vouch_tickets = [t for t in tickets
                              if t["account_id"] == subj["account_id"]
                              and t["status"] == "approved"
                              and t.get("app", subj["app"]) == subj["app"]
                              and t.get("role", subj["entitlement"]) == subj["entitlement"]]
            assert vouch_tickets, (
                "no approved vouch ticket found for the contractor's account"
            )

        elif narrative == "TransferKeptOldAccess":
            row = hr_by_id[subj["employee_id"]]
            assert row["department"].strip().lower() == "finance & accounting"
            rows_acct = ent_by_acct[subj["account_id"]]
            assert any(r["app"] == "Helix ITSM" and r["role"] == "Change Approver"
                       for r in rows_acct), "old-department access not found on account"

        elif narrative == "SoDConflictWithCompensatingControl":
            rows_acct = ent_by_acct[subj["account_id"]]
            assert any(r["app"] == "Atlas ERP" and r["role"] == "Vendor Admin"
                       for r in rows_acct), "missing Vendor Admin leg of the SoD pair"
            assert any(r["app"] == "Atlas ERP" and r["role"] == "AP Manager"
                       for r in rows_acct), "missing AP Manager leg of the SoD pair"

        elif narrative in ("ApprovedServiceAccount", "BreakGlassDormant"):
            rows_acct = ent_by_acct[subj["account_id"]]
            assert any(r["account_name"] in w.service_accounts for r in rows_acct), (
                "no entitlement row on this account uses a registered service-account name"
            )

        elif narrative == "EmployeeOnLeave":
            row = hr_by_id[subj["employee_id"]]
            assert row["status"] == "on_leave"
            assert row["term_date"] == ""

        elif narrative == "ExemptedSoDPair":
            row = hr_by_id[subj["employee_id"]]
            assert row["title"] == "Controller"
            rows_acct = ent_by_acct[subj["account_id"]]
            assert any(r["app"] == "Atlas ERP" and r["role"] == "Vendor Admin"
                       for r in rows_acct), "missing Vendor Admin leg of the exempted pair"
            assert any(r["app"] == "Atlas ERP" and r["role"] == "AP Manager"
                       for r in rows_acct), "missing AP Manager leg of the exempted pair"

        elif narrative == "PriorReviewCoverageGap":
            assert subj["app"] not in prior_apps       # genuinely absent from prior review
            omitted_apps.add(subj["app"])

        elif narrative == "NewAppNoPriorReview":
            assert subj["app"] not in prior_apps       # the trap: also absent, but expected
            omitted_apps.add(subj["app"])

        else:
            pytest.fail(f"no coherence check for narrative {narrative!r}")

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
