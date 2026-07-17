from __future__ import annotations

import json
from collections import Counter


def case_to_dict(case) -> dict:
    return {
        "case_id": case.case_id,
        "narrative": case.narrative,
        "class": case.finding_class,
        "scope": case.scope,
        "subject": case.subject,
        "expected": case.expected,
        "rationale_must_reference": case.rationale_must_reference,
    }


def build_answer_key(seed: int, quarter: str, cases, clean_count: int) -> dict:
    by_class = Counter(c.finding_class for c in cases)
    counts = {
        "must_catch": by_class.get("must_catch", 0),
        "judgment": by_class.get("judgment", 0),
        "trap": by_class.get("trap", 0),
        "clean": clean_count,
    }
    return {
        "seed": seed,
        "quarter": quarter,
        "counts": counts,
        "cases": [case_to_dict(c) for c in cases],
    }


def write_answer_key(path: str, key: dict) -> None:
    with open(path, "w") as f:
        json.dump(key, f, indent=2, sort_keys=True)
