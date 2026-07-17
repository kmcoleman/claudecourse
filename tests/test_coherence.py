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
