import os
from meridian.kit_export import kit_export


def test_kit_export_writes_data_without_answer_key(tmp_path):
    kit = tmp_path / "meridian-capstone"
    kit_export(20260715, "2026-Q3", str(kit))
    data = kit / "data" / "2026-Q3"
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv", "applications.json", "sod_matrix.json",
                 "service_accounts.json"]:
        assert (data / name).exists(), name
    assert (data / "policies" / "access-control-policy.md").exists()
    # the answer key must never appear anywhere under the kit
    for root, _dirs, files in os.walk(kit):
        assert "answer_key.json" not in files
