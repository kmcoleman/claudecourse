import csv
import filecmp
import os
from collections import Counter

from meridian.generate import generate


def _gen(tmp, seed=20260715, quarter="2026-Q3"):
    out = tmp / quarter
    key = tmp / "answer_key.json"
    generate(seed, quarter, str(out), str(key))
    return out, key


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


def test_seed_variation_changes_selection(tmp_path):
    import json
    _o1, k1 = _gen(tmp_path / "s1", seed=1)
    _o2, k2 = _gen(tmp_path / "s2", seed=2)
    apps1 = {c["subject"]["app"] for c in json.load(open(k1))["cases"]
             if c["narrative"] == "PriorReviewCoverageGap"}
    apps2 = {c["subject"]["app"] for c in json.load(open(k2))["cases"]
             if c["narrative"] == "PriorReviewCoverageGap"}
    assert apps1 != apps2
