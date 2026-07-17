import json
from meridian.models import Case
from meridian.answer_key import build_answer_key, write_answer_key


def _cases():
    return [
        Case("c1", "TerminatedWithActiveAdmin", "must_catch", "account",
             {"account_id": "A1"}, {"recommendation": "revoke"}, ["term_date"]),
        Case("c2", "PriorReviewCoverageGap", "judgment", "application",
             {"app": "Box"}, {"recommendation": "review"}, ["not_in_prior_review"]),
        Case("c3", "ExemptedSoDPair", "trap", "account", {"account_id": "A2"}, {}, []),
    ]


def test_counts_tally_by_class():
    key = build_answer_key(123, "2026-Q4", _cases(), clean_count=1155)
    assert key["counts"] == {"must_catch": 1, "judgment": 1, "trap": 1, "clean": 1155}
    assert key["seed"] == 123 and key["quarter"] == "2026-Q4"


def test_write_and_reload(tmp_path):
    key = build_answer_key(123, "2026-Q4", _cases(), clean_count=1155)
    path = tmp_path / "answer_key.json"
    write_answer_key(str(path), key)
    reloaded = json.load(open(path))
    assert len(reloaded["cases"]) == 3
    assert reloaded["cases"][2]["expected"] == {}
