"""Day 3 checkpoint — verifies the learner's policy Skills and cited findings.

Day 3 asks the learner to turn three of Meridian's written policies into Agent
Skills, then rewire triage so every finding cites the clause it came from:

    .claude/skills/sod-policy/SKILL.md
    .claude/skills/privileged-access-standard/SKILL.md
    .claude/skills/contractor-access-standard/SKILL.md
    findings.json    now carries a populated policy_citations on every finding

Numbers below come from the shipped seed-locked 2026-Q3 export, so they are
exact rather than approximate. If no Skills directory exists yet the whole
module skips — a fresh clone stays green.
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

SKILLS_DIR = ROOT / ".claude" / "skills"
FINDINGS = ROOT / "findings.json"
EXEMPTIONS = ROOT / "exemptions.json"

SOD = "sod-policy"
PRIV = "privileged-access-standard"
CONTRACTOR = "contractor-access-standard"

if not SKILLS_DIR.exists():
    pytest.skip(
        "No .claude/skills/ directory found. Work through Day 3 first — this "
        "module checks the three policy Skills and the cited findings.json.",
        allow_module_level=True,
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _found_skills():
    """Every SKILL.md under .claude/skills/, by directory name."""
    return {p.parent.name: p for p in SKILLS_DIR.glob("*/SKILL.md")}


def _skill_text(slug):
    found = _found_skills()
    if slug not in found:
        pytest.fail(
            f".claude/skills/{slug}/SKILL.md is missing. A Skill is a *directory* "
            f"containing SKILL.md — a flat .claude/skills/{slug}.md is never "
            f"loaded. Found instead: {sorted(found) or 'nothing'}"
        )
    return found[slug].read_text()


def _frontmatter(slug):
    text = _skill_text(slug)
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        pytest.fail(
            f"{slug}/SKILL.md has no YAML frontmatter. It must open with a '---' "
            "line, carry name and description, and close with another '---'."
        )
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip().strip("\"'")
    return fields


def _body(slug):
    """The Skill body, lowercased, with frontmatter stripped."""
    text = _skill_text(slug)
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL).lower()


def _json(path):
    if not path.exists():
        pytest.fail(f"{path.name} is missing — Day 3 expects it at the repo root.")
    return json.load(open(path))


def _by_category(cat):
    return [f for f in _json(FINDINGS) if f["category"] == cat]


# --------------------------------------------------------------------------
# Cycle 1-3 — the Skill files themselves
# --------------------------------------------------------------------------

@pytest.mark.parametrize("slug", [SOD, PRIV, CONTRACTOR])
def test_skill_exists_as_a_directory_with_skill_md(slug):
    _skill_text(slug)


@pytest.mark.parametrize("slug", [SOD, PRIV, CONTRACTOR])
def test_skill_frontmatter_is_valid(slug):
    fm = _frontmatter(slug)
    name = fm.get("name", "")
    desc = fm.get("description", "")

    assert name, f"{slug}/SKILL.md frontmatter needs a name field"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", name), (
        f"name '{name}' must be lowercase letters, numbers and hyphens only, "
        "max 64 characters"
    )
    assert "anthropic" not in name and "claude" not in name, (
        f"name '{name}' uses a reserved word"
    )
    assert desc, f"{slug}/SKILL.md frontmatter needs a description field"
    assert len(desc) <= 1024, "description is capped at 1024 characters"
    assert len(desc) > 30, (
        f"description for {slug} is too thin to route on. It must say what the "
        "Skill does *and* when to apply it — that is the only text Claude sees "
        "when deciding whether to load the Skill."
    )


def test_sod_skill_encodes_the_rule_and_its_exemption():
    body = _body(SOD)
    assert "acp-4.1" in body, (
        "the SoD Skill must cite ACP-4.1 — the clause that actually forbids one "
        "person holding conflicting duties"
    )
    assert "acp-4.2" in body, (
        "the SoD Skill must cite ACP-4.2 — without the exemption the Skill "
        "reports three Controllers as false positives"
    )
    assert "controller" in body, "ACP-4.2 is scoped to the Controller role"


def test_privileged_skill_encodes_dormancy_and_break_glass():
    body = _body(PRIV)
    assert "180" in body, "the Privileged Access Standard sets a 180-day dormancy window"
    assert "break-glass" in body or "break glass" in body, (
        "registered break-glass accounts are exempt from the dormancy rule — "
        "without that, emergency.admin becomes a false positive"
    )


def test_contractor_skill_encodes_the_sow_rule():
    body = _body(CONTRACTOR)
    assert "sow" in body or "statement-of-work" in body or "statement of work" in body, (
        "contractor access is governed by the statement-of-work end date"
    )


# --------------------------------------------------------------------------
# Cycle 4 — findings now cite their clause
# --------------------------------------------------------------------------

def test_findings_still_match_the_contract():
    jsonschema.validate(_json(FINDINGS), SCHEMA)


def test_every_finding_cites_a_policy():
    uncited = [
        (f.get("account_id"), f["category"])
        for f in _json(FINDINGS)
        if not [c for c in (f.get("policy_citations") or []) if c.strip()]
    ]
    assert not uncited, (
        f"{len(uncited)} finding(s) carry no policy_citations, e.g. {uncited[:3]}. "
        "A finding a reviewer cannot trace to a clause is not audit-defensible."
    )


def test_all_three_policy_categories_are_represented():
    cats = {f["category"] for f in _json(FINDINGS)}
    missing = {"sod_conflict", "dormant_privileged", "contractor_overstay"} - cats
    assert not missing, (
        f"findings.json has no {sorted(missing)} findings — one of the three "
        f"Skills is not reaching triage. Categories present: {sorted(cats)}"
    )


def test_sod_findings_survive_and_cite_the_real_clause():
    sod = _by_category("sod_conflict")
    got = sorted({f["account_id"] for f in sod})
    assert got == ["A000384", "A001115"], (
        f"expected SoD conflicts on A000384 and A001115, got {got}"
    )
    for f in sod:
        cites = " ".join(f.get("policy_citations") or [])
        assert "ACP-4.1" in cites or "SoD" in cites, (
            f"{f['account_id']} cites {cites!r}; an SoD conflict should point at "
            "ACP-4.1 or the SoD Policy, not an invented section number"
        )


def test_controllers_are_still_exempt_not_reported():
    controllers = {"A000387", "A000674", "A001125"}
    reported = {f.get("account_id") for f in _by_category("sod_conflict")} & controllers
    assert not reported, (
        f"{sorted(reported)} hold AP Manager + Vendor Admin under the standing "
        "ACP-4.2 exemption — reporting them is a false positive"
    )


def test_dormant_privileged_finds_the_three_stale_vault_admins():
    got = sorted({f["account_id"] for f in _by_category("dormant_privileged")})
    assert got == ["A000012", "A000598", "A000742"], (
        f"expected the three dormant Vault Admin accounts, got {got}. All three "
        "last logged in more than 180 days before quarter end and hold no "
        "approving ticket."
    )


def test_break_glass_is_exempted_not_flagged_dormant():
    breakglass = {"A001159", "A001199"}
    flagged = {f.get("account_id") for f in _by_category("dormant_privileged")} & breakglass
    assert not flagged, (
        f"{sorted(flagged)} are the registered emergency.admin break-glass "
        "accounts (data/2026-Q3/service_accounts.json). The Privileged Access "
        "Standard exempts them from the dormancy rule — flagging them is a "
        "false positive."
    )


def test_break_glass_exemptions_are_recorded_rather_than_dropped():
    if not EXEMPTIONS.exists():
        pytest.fail(
            "exemptions.json is missing. Suppressing a break-glass account "
            "without recording why is indistinguishable from missing it."
        )
    ids = {e.get("account_id") for e in _json(EXEMPTIONS)}
    missing = {"A001159", "A001199"} - ids
    assert not missing, (
        f"{sorted(missing)} were suppressed under the break-glass exemption but "
        "never recorded in exemptions.json"
    )


def test_contractor_overstay_covers_all_four_lapsed_accounts():
    got = sorted({f["account_id"] for f in _by_category("contractor_overstay")})
    assert got == ["A000686", "A000741", "A001185", "A001195"], (
        f"expected the four accounts held by the three expired-SOW contractors, "
        f"got {got}. A000686 is Jamie Alvarez's second account — it lapses with "
        "the same SOW and is easy to miss."
    )


def test_vpn_tickets_did_not_clear_the_contractors():
    """The three VPN tickets look like renewals but reference no renewed SOW."""
    accounts = {"A000741", "A001185", "A001195"}
    found = {f["account_id"] for f in _by_category("contractor_overstay")}
    assert accounts <= found, (
        f"{sorted(accounts - found)} were cleared by an approved ticket dated "
        "just before the SOW end date. Those tickets grant VPN/User only and "
        "reference no renewed SOW — under the Contractor Access Standard they "
        "do not extend access."
    )
