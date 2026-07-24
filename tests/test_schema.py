import json
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.load(open(ROOT / "src" / "meridian_capstone" / "contract" / "findings.schema.json"))


def _validate(findings):
    jsonschema.validate(findings, SCHEMA)


def test_empty_list_is_valid():
    _validate([])


def test_sample_findings_valid():
    sample = json.load(open(ROOT / "examples" / "sample_findings.json"))
    _validate(sample)


def test_account_finding_requires_account_id():
    bad = [{
        "scope": "account", "account_id": None, "employee_id": "E1",
        "app": "Vault", "entitlement": "Admin", "category": "dormant_privileged",
        "severity": "high", "recommendation": "revoke", "rationale": "x",
        "evidence": [{"source": "entitlements", "detail": "y"}],
        "policy_citations": [], "confidence": 0.9,
    }]
    import pytest
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)


def test_bad_category_rejected():
    bad = [{
        "scope": "application", "account_id": None, "employee_id": None,
        "app": "Box", "entitlement": None, "category": "not_a_category",
        "severity": "medium", "recommendation": "review", "rationale": "x",
        "evidence": [{"source": "prior_review", "detail": "y"}],
        "policy_citations": [], "confidence": 0.5,
    }]
    import pytest
    with pytest.raises(jsonschema.ValidationError):
        _validate(bad)
