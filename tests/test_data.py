import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "2026-Q3"


def test_all_export_files_present():
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv", "applications.json", "sod_matrix.json",
                 "service_accounts.json"]:
        assert (DATA / name).exists(), name
    assert (DATA / "policies" / "access-control-policy.md").exists()


def test_no_answer_key_shipped():
    root = Path(__file__).resolve().parent.parent
    assert not (root / "answer_key.json").exists()
    for p in root.rglob("answer_key.json"):
        raise AssertionError(f"answer key leaked into the kit: {p}")


def test_entitlements_parse_and_have_rows():
    rows = list(csv.DictReader(open(DATA / "entitlements.csv")))
    assert len(rows) > 10000
    assert {"account_id", "account_name", "app", "role"} <= set(rows[0])


def test_applications_has_22_apps():
    apps = json.load(open(DATA / "applications.json"))
    assert len(apps) == 22
