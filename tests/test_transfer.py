"""Day 5 checkpoint — the pipeline transfers to an unseen quarter (Q4).

Day 5 runs the exact Day 4 pipeline against a fresh quarter (Q4) with no code
changes. The whole point is generalization: the system must have learned the
*pattern* (whoever holds Vendor Admin + AP Manager, whichever Controller is
exempt under ACP-4.2, whichever contractor is past SOW) rather than *memorized*
Q3's specific people, IDs, or exact counts. So this module checks the Q4 answer
against Q4 ground truth — a different cast from Q3 — and confirms the Day 4
enforcement layer travels.

Q4 ships pre-generated in the kit (data/2026-Q4/), produced once by the same
world design under a fixed seed (20261015). Students read it in Day 5 Cycle 1
rather than running the generator, so these inputs are always present.

The Q4 run writes its findings to a quarter-stamped file, findings.2026-Q4.json,
so Q3's findings.json stays intact for the Day 4 regression check. Tests that
need the learner's Q4 artifacts self-skip until those artifacts are produced.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA_Q4 = ROOT / "data" / "2026-Q4"
SCHEMA = json.load(
    open(ROOT / "src" / "meridian_capstone" / "contract" / "findings.schema.json")
)

FINDINGS_Q4 = ROOT / "findings.2026-Q4.json"
EXEMPTIONS_Q4 = ROOT / "exemptions.2026-Q4.json"
AUDIT_Q4 = ROOT / "audit" / "2026-Q4.jsonl"
GUARD = ROOT / ".claude" / "hooks" / "examples" / "secret_guard.py"

# Q4 ground truth — seed 20261015. A completely different cast from Q3, produced
# by the same world design. These assertions line up with the data/2026-Q4/ that
# ships in the kit; if it has been edited or replaced, they will fail.
Q4_SOD = ["A000276", "A000523"]                       # Catherine Berry, David Roberts
Q4_DORMANT = ["A000690", "A000820", "A000879"]        # all Vault / Admin
Q4_CONTRACTOR = ["A000133", "A000157", "A000749"]     # 3 accounts (no twin this seed)
Q4_EXEMPT = {"A000518", "A000895", "A001168",         # three ACP-4.2 Controllers
             "A000504", "A001045"}                    # two break-glass emergency.admin
Q3_ACCOUNTS = {"A000384", "A001115", "A000012", "A000598", "A000742",
               "A000686", "A000741", "A001185", "A001195"}

# Q4 ships pre-generated in the kit (data/2026-Q4/), so these inputs are always
# present — no module-level skip guarding on their existence. The per-test
# skips below still fire until the *learner* produces the Q4 answer artifacts
# (findings.2026-Q4.json, exemptions.2026-Q4.json, audit/2026-Q4.jsonl).


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _json(path):
    if not path.exists():
        pytest.skip(
            f"{path.name} not produced yet — Day 5 Cycle 4 writes the Q4 answer. "
            "Run the pipeline against data/2026-Q4 first."
        )
    return json.load(open(path))


def _q4_findings():
    return _json(FINDINGS_Q4)


def _by_category(cat):
    return [f for f in _q4_findings() if f["category"] == cat]


# --------------------------------------------------------------------------
# Cycle 1 — a fresh quarter exists, same company
# --------------------------------------------------------------------------

def test_q4_inputs_were_generated():
    for name in ("hr_roster.csv", "entitlements.csv",
                 "access_tickets.json", "prior_review.csv"):
        assert (DATA_Q4 / name).exists(), (
            f"data/2026-Q4/{name} is missing. Q4 ships pre-generated in the kit — "
            "check out data/2026-Q4/ from the repo (Day 5 Cycle 1)."
        )
    assert (DATA_Q4 / "policies").is_dir(), "data/2026-Q4/policies/ is missing."


def test_q4_is_the_expected_seed():
    """The same company (1190 people, 1200 accounts) under a new seed."""
    hr_rows = (DATA_Q4 / "hr_roster.csv").read_text().splitlines()
    assert len(hr_rows) - 1 == 1190, (
        f"Expected 1190 HR rows for seed 20261015, got {len(hr_rows) - 1}. If this "
        "is off, the pre-shipped data/2026-Q4/ is not the seed-20261015 quarter "
        "the ground-truth checks below line up with — restore it from the repo."
    )


# --------------------------------------------------------------------------
# Cycle 4 — the Q4 answer matches Q4 ground truth (a different cast)
# --------------------------------------------------------------------------

def test_q4_findings_match_the_contract():
    jsonschema.validate(_q4_findings(), SCHEMA)


def test_q4_has_eight_findings_across_three_categories():
    findings = _q4_findings()
    counts = {c: len(_by_category(c)) for c in
              ("sod_conflict", "dormant_privileged", "contractor_overstay")}
    assert counts == {"sod_conflict": 2, "dormant_privileged": 3,
                      "contractor_overstay": 3}, (
        f"Expected the Q4 breakdown (2 / 3 / 3), got {counts}. Q4 has eight "
        "findings, not nine — this quarter no contractor holds a second account, "
        "so a pipeline pinned to Q3's count of 9 has memorized the answer."
    )
    assert len(findings) == 8, f"Expected 8 Q4 findings total, got {len(findings)}."


def test_q4_account_sets_are_the_new_cast():
    expected = {
        "sod_conflict": Q4_SOD,
        "dormant_privileged": Q4_DORMANT,
        "contractor_overstay": Q4_CONTRACTOR,
    }
    for cat, want in expected.items():
        got = sorted({f["account_id"] for f in _by_category(cat)})
        assert got == sorted(want), (
            f"{cat}: expected Q4 accounts {sorted(want)}, got {got}. The pipeline "
            "produced a different set than Q4 ground truth."
        )


def test_q4_findings_are_not_q3s_answer():
    """The tell-tale of a split-brain run: Q4 findings naming Q3 people.

    If .mcp.json still pins MERIDIAN_DATA_DIR=data/2026-Q3, the ledger-reader
    keeps reading Q3 even when run_review points at Q4 — the run finishes clean
    but returns Q3's accounts. Catch that here.
    """
    got = {f.get("account_id") for f in _q4_findings()}
    leaked = got & Q3_ACCOUNTS
    assert not leaked, (
        f"The Q4 findings still name Q3 accounts {sorted(leaked)}. The pipeline is "
        "reading Q3 data for a Q4 run — check MERIDIAN_DATA_DIR in .mcp.json."
    )


def test_q4_every_finding_cites_a_policy():
    uncited = [
        (f.get("account_id"), f["category"])
        for f in _q4_findings()
        if not [c for c in (f.get("policy_citations") or []) if c.strip()]
    ]
    assert not uncited, (
        f"{len(uncited)} Q4 finding(s) carry no policy_citations, e.g. "
        f"{uncited[:3]}. Transfer means comparable quality, not just a file that "
        "exists."
    )


def test_q4_exemptions_are_the_new_cast():
    exemptions = _json(EXEMPTIONS_Q4)
    ids = {e.get("account_id") for e in exemptions}
    missing = Q4_EXEMPT - ids
    assert not missing, (
        f"{sorted(missing)} should be recorded as Q4 exemptions (three ACP-4.2 "
        "Controllers, two break-glass emergency.admin accounts) but are absent. "
        "A dropped exemption is indistinguishable from a missed finding — and if "
        "the Controllers are missing here, they were probably flagged instead."
    )


# --------------------------------------------------------------------------
# Cycle 4 — the enforcement layer travels to the new seed
# --------------------------------------------------------------------------

def test_q4_audit_log_filled():
    if not AUDIT_Q4.exists():
        pytest.skip(
            "audit/2026-Q4.jsonl not found yet. After the Q4 run, the PostToolUse "
            "audit hook should fill it — set MERIDIAN_QUARTER=2026-Q4 so the hook "
            "writes the Q4 log rather than the Q3 one."
        )
    lines = [ln for ln in AUDIT_Q4.read_text().splitlines() if ln.strip()]
    assert lines, "audit/2026-Q4.jsonl exists but is empty — no write was recorded."
    entry = json.loads(lines[-1])
    assert set(entry) == {"ts", "tool", "path", "session_id"}, (
        f"Each audit line needs ts, tool, path, session_id — got {sorted(entry)}."
    )


def test_guard_still_blocks_a_secret_on_q4():
    """The secret guard is pattern-based, so it must fire on Q4 exactly as on Q3."""
    if not GUARD.exists():
        pytest.skip("secret_guard.py stub is missing from .claude/hooks/examples/.")
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "findings.2026-Q4.json",
                "content": "rationale: leaked on the new seed sk-fake-secret-12345",
            },
        }),
        capture_output=True, text=True, env=dict(os.environ),
    )
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny", (
        "The guard let a secret-bearing Q4 write through. Enforcement that only "
        "works on Q3 is not enforcement."
    )
