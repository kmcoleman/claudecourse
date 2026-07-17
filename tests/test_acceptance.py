import csv
import filecmp
import json
from datetime import datetime

from meridian.generate import generate


def _gen(tmp, seed=20260715, quarter="2026-Q3"):
    out = tmp / quarter
    key = tmp / "answer_key.json"
    generate(seed, quarter, str(out), str(key))
    return out, key


def _parse_date(s):
    """Entitlements CSV mixes ISO (YYYY-MM-DD) and US (MM/DD/YYYY) formats;
    HR dates are always ISO (tried first). Blank -> None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _derived_account_name(full_name):
    parts = full_name.split()
    return f"{parts[0].lower()}.{parts[-1].lower()}"


def test_determinism_byte_identical(tmp_path):
    a, ka = _gen(tmp_path / "a")
    b, kb = _gen(tmp_path / "b")
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv"]:
        assert filecmp.cmp(a / name, b / name, shallow=False), f"{name} differs"
    assert open(ka).read() == open(kb).read()


def test_counts_hit_targets(tmp_path):
    import json
    _out, key = _gen(tmp_path)
    k = json.load(open(key))
    assert k["counts"]["must_catch"] == 24
    assert k["counts"]["judgment"] == 9
    assert k["counts"]["trap"] == 13


def test_anti_leak_planted_ids_not_clustered(tmp_path):
    import json
    out, key = _gen(tmp_path)
    k = json.load(open(key))
    planted_accts = [c["subject"].get("account_id") for c in k["cases"]
                     if c["subject"].get("account_id")]
    nums = sorted(int(a[1:]) for a in planted_accts)
    # planted account ids should span a wide range, not sit in one contiguous block
    assert nums[-1] - nums[0] > len(nums) * 5


def test_no_unplanted_grant_before_hire(tmp_path):
    # Core invariant: the ONLY entitlements dated before their holder's hire_date
    # are the deliberate GrantBeforeHireDate planted grants. Nothing else, on any
    # account (clean or trap), may carry a pre-hire grant.
    for seed in (1, 7, 42, 20260715):
        out, key_path = _gen(tmp_path / f"s{seed}", seed=seed)
        ent = list(csv.DictReader(open(out / "entitlements.csv")))
        hr = list(csv.DictReader(open(out / "hr_roster.csv")))
        key = json.load(open(key_path))

        # account_name -> hire_date, keeping only names with a single unambiguous
        # hire_date (guards against Faker full-name collisions in HR).
        by_name = {}
        for r in hr:
            hd = _parse_date(r["hire_date"])
            if hd is not None:
                by_name.setdefault(_derived_account_name(r["full_name"]), set()).add(hd)
        hire_by_name = {n: next(iter(s)) for n, s in by_name.items() if len(s) == 1}

        # Entitlements carry no employee link, and a ~10% "mismatch" nickname can
        # coincide with another person's real first.last name. Only trust a name
        # that resolves to a single account_id on the IAM side -- otherwise the
        # holder is ambiguous and its true hire_date is unknown.
        accts_by_name = {}
        for r in ent:
            accts_by_name.setdefault(r["account_name"], set()).add(r["account_id"])

        gbh_accounts = {c["subject"]["account_id"] for c in key["cases"]
                        if c["narrative"] == "GrantBeforeHireDate"}
        assert gbh_accounts, f"seed {seed}: expected GrantBeforeHireDate planted cases"

        for r in ent:
            hire = hire_by_name.get(r["account_name"])
            if hire is None or len(accts_by_name[r["account_name"]]) != 1:
                continue  # mismatch/service/ambiguous account -> hire_date unknown
            granted = _parse_date(r["granted_date"])
            if granted is not None and granted < hire:
                assert r["account_id"] in gbh_accounts, (
                    f"seed {seed}: account {r['account_id']} ({r['account_name']}) holds a "
                    f"grant on {r['app']} dated {granted} before hire {hire}, "
                    "but is not a GrantBeforeHireDate subject"
                )


def test_seed_variation_changes_selection(tmp_path):
    import json
    _o1, k1 = _gen(tmp_path / "s1", seed=1)
    _o2, k2 = _gen(tmp_path / "s2", seed=2)
    apps1 = {c["subject"]["app"] for c in json.load(open(k1))["cases"]
             if c["narrative"] == "PriorReviewCoverageGap"}
    apps2 = {c["subject"]["app"] for c in json.load(open(k2))["cases"]
             if c["narrative"] == "PriorReviewCoverageGap"}
    assert apps1 != apps2
