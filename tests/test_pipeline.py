"""Sub-tasks 23-25 checkpoint — the subagent pipeline reproduces the Q3 answer.

Sub-tasks 23-25 (Themes E-F) take the single-pass triage of sub-task 19 apart and
rebuild it as an orchestrator delegating to specialist subagents (a ledger-reader
over MCP, a policy-applier, a findings-writer), each defined under
.claude/agents/. Decomposition changes HOW the findings are produced — it must
not change WHAT they are. So this module asserts the full-Q3 findings.json still
carries the exact nine findings and five exemptions sub-task 19 established, plus
the pieces sub-tasks 23-25 add: a specialist team and the frozen run_review
contract.

The module self-skips until .claude/agents/ exists, so a clone that has not
reached sub-task 23 stays green.
"""
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "2026-Q3"
SCHEMA = json.load(
    open(ROOT / "src" / "meridian_capstone" / "contract" / "findings.schema.json")
)

AGENTS_DIR = ROOT / ".claude" / "agents"
FINDINGS = ROOT / "findings.json"
EXEMPTIONS = ROOT / "exemptions.json"

if not AGENTS_DIR.exists():
    pytest.skip(
        "No .claude/agents/ directory found. Work through sub-tasks 23-25 "
        "first — this module checks the subagent pipeline and its Q3 output.",
        allow_module_level=True,
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _json(path):
    if not path.exists():
        pytest.fail(f"{path.name} is missing — sub-tasks 23-25 regenerate it at the repo root.")
    return json.load(open(path))


def _by_category(cat):
    return [f for f in _json(FINDINGS) if f["category"] == cat]


def _agent_frontmatter():
    """{name: fields} for every .claude/agents/*.md with parseable frontmatter."""
    out = {}
    for md in AGENTS_DIR.glob("*.md"):
        text = md.read_text()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if not m:
            continue
        fields = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "\t", "#")):
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip().strip("\"'")
        if "name" in fields:
            out[fields["name"]] = fields
    return out


# --------------------------------------------------------------------------
# Sub-tasks 23-24 — the specialist team
# --------------------------------------------------------------------------

def test_a_specialist_team_exists():
    agents = _agent_frontmatter()
    assert len(agents) >= 3, (
        "Sub-tasks 23-24 decompose triage into at least three specialists (a "
        "ledger reader, a policy applier, a findings writer) as "
        ".claude/agents/*.md "
        f"files. Found {len(agents)}: {sorted(agents) or 'none'}."
    )


def test_every_agent_has_name_and_description():
    for md in AGENTS_DIR.glob("*.md"):
        text = md.read_text()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        assert m, (
            f"{md.name} has no YAML frontmatter. A subagent file opens with a "
            "'---' block carrying name and description."
        )
        block = m.group(1)
        assert re.search(r"^name:\s*\S", block, re.MULTILINE), f"{md.name} needs a name."
        assert re.search(r"^description:\s*\S", block, re.MULTILINE), (
            f"{md.name} needs a description — it is the text Claude routes on when "
            "deciding whether to delegate to this specialist."
        )


# --------------------------------------------------------------------------
# Sub-task 25 — the frozen contract still holds
# --------------------------------------------------------------------------

def test_run_review_keeps_the_frozen_signature():
    from meridian_capstone.contract.run_review import run_review
    import inspect

    params = list(inspect.signature(run_review).parameters)
    assert params[:2] == ["export_dir", "limit"], (
        "The grader calls run_review(export_dir, limit=None). Keep that exact "
        f"signature; got parameters {params}."
    )


# --------------------------------------------------------------------------
# Sub-task 25 — the decomposed pipeline reproduces sub-task 19's answer, exactly
# --------------------------------------------------------------------------

def test_findings_match_the_contract():
    jsonschema.validate(_json(FINDINGS), SCHEMA)


def test_nine_findings_across_three_categories():
    findings = _json(FINDINGS)
    counts = {c: len(_by_category(c)) for c in
              ("sod_conflict", "dormant_privileged", "contractor_overstay")}
    assert counts == {"sod_conflict": 2, "dormant_privileged": 3, "contractor_overstay": 4}, (
        f"Expected the sub-task 19 breakdown (2 / 3 / 4), got {counts}. Decomposing "
        "triage into subagents must not change the answer — only how it is "
        "produced."
    )
    assert len(findings) == 9, f"Expected 9 findings total, got {len(findings)}."


def test_every_finding_still_cites_a_policy():
    uncited = [
        (f.get("account_id"), f["category"])
        for f in _json(FINDINGS)
        if not [c for c in (f.get("policy_citations") or []) if c.strip()]
    ]
    assert not uncited, (
        f"{len(uncited)} finding(s) lost their policy_citations in the rewrite, "
        f"e.g. {uncited[:3]}. The findings-writer must carry citations through."
    )


def test_account_sets_are_unchanged():
    expected = {
        "sod_conflict": ["A000384", "A001115"],
        "dormant_privileged": ["A000012", "A000598", "A000742"],
        "contractor_overstay": ["A000686", "A000741", "A001185", "A001195"],
    }
    for cat, want in expected.items():
        got = sorted({f["account_id"] for f in _by_category(cat)})
        assert got == want, (
            f"{cat}: expected accounts {want}, got {got}. The subagent pipeline "
            "produced a different set than sub-task 19 — a specialist changed the "
            "answer rather than just the plumbing."
        )


def test_five_exemptions_survived_the_rewrite():
    if not EXEMPTIONS.exists():
        pytest.fail(
            "exemptions.json is missing. The five suppressions (three ACP-4.2 "
            "Controllers, two break-glass accounts) must survive decomposition."
        )
    ids = {e.get("account_id") for e in _json(EXEMPTIONS)}
    expected = {"A000387", "A000674", "A001125", "A001159", "A001199"}
    missing = expected - ids
    assert not missing, (
        f"{sorted(missing)} were recorded as exemptions in sub-task 19 but are "
        "absent now. A dropped exemption is indistinguishable from a missed "
        "finding."
    )
