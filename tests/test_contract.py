import json
from pathlib import Path
import jsonschema
from meridian_capstone.contract.run_review import run_review

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.load(open(ROOT / "src" / "meridian_capstone" / "contract" / "findings.schema.json"))


def test_stub_returns_empty_list():
    result = run_review(ROOT / "data" / "2026-Q3")
    assert result == []


def test_stub_output_validates_against_schema():
    jsonschema.validate(run_review(ROOT / "data" / "2026-Q3"), SCHEMA)


def test_accepts_limit_kwarg():
    assert run_review(ROOT / "data" / "2026-Q3", limit=5) == []
