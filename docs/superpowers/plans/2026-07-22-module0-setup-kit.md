# Module 0 Setup Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the clone-and-go `meridian-capstone` kit — pre-generated Q3 data (no answer key), the frozen `run_review → findings.json` contract + JSON Schema, a read-only Meridian MCP server, a green-light smoke test with a mandatory live-API check, and a Windows-first bootstrap — plus the small generator enhancement that makes each export self-contained.

**Architecture:** Two repos. Part A enhances the existing **generator** (`meridian` package in the `claudecourse` repo) to emit three reference JSONs into every export and adds a `kit_export` CLI that copies an export into the kit *without* the answer key. Part B builds the new **`meridian-capstone`** kit repo learners clone. The kit's Python components (schema, contract stub, MCP server, tests) are cross-platform and fully testable on this macOS build machine; the Windows bootstrap is authored against verified `winget` commands and syntax-checked, with a one-time Windows execution left to the instructor.

**Tech Stack:** Python 3.11+; `claude-agent-sdk` (Agent SDK, async `query`); `mcp` (official MCP SDK, `mcp.server.fastmcp.FastMCP`); `jsonschema`; `pytest`. Windows bootstrap: PowerShell + `winget`. Claude Code via npm `@anthropic-ai/claude-code`.

## Global Constraints

- **Two repos, explicit per task.** Part A tasks operate in `/Users/kev/dev/claudecourse` (generator). Part B tasks operate in `/Users/kev/dev/meridian-capstone` (the kit, created in Task 3). Every task names its repo.
- **The answer key never enters the kit.** `kit_export` and every kit task must never write or copy `answer_key.json` into `meridian-capstone`.
- **Determinism (generator side).** No `datetime.now()`; the generator stays deterministic. Reference JSONs are emitted from the same `world`/`selection`/`quarter_start` already in `generate()`.
- **The contract is frozen.** `run_review(export_dir: Path, limit: int | None = None) -> list[dict]`; findings validate against `contract/findings.schema.json`. Field set per spec §"The frozen contract". Do not add or rename fields.
- **Mandatory API green light.** The full `pytest` run includes a real Claude call (`tests/test_api.py`, marked `@pytest.mark.api`). `pytest -m "not api"` is the free offline subset.
- **Verified toolchain values (confirmed against live docs 2026-07-22):**
  - Agent SDK: `pip install claude-agent-sdk` (>=0.1.59); async `from claude_agent_sdk import query`; reads `ANTHROPIC_API_KEY`; does NOT auto-load `.env`.
  - MCP: `pip install mcp`; `from mcp.server.fastmcp import FastMCP`; server runs over stdio via `mcp.run()`. (Task 3 verifies this exact import; documented fallback is the standalone `fastmcp` package if the official path has moved.)
  - Claude Code: npm `@anthropic-ai/claude-code` (Node 22+); VS Code extension id `anthropic.claude-code`.
  - `.mcp.json`: `{"mcpServers": {"<name>": {"type": "stdio", "command": "python", "args": ["-m", "mcp.server"], "env": {...}}}}`.
  - winget ids: `Python.Python.3.12`, `Git.Git`, `OpenJS.NodeJS.LTS`, `Microsoft.VisualStudioCode`; install `winget install -e --id <Id> --silent --accept-package-agreements --accept-source-agreements --no-upgrade`; check `winget list --id <Id> -e` (exit 0 = present).
- **Kit Q3 seed:** `20260715`, quarter `2026-Q3` (fixed for the shipped kit).

---

## File Structure

**Part A — generator (`claudecourse` repo):**
```
meridian/emit.py            # + write_applications / write_sod_matrix / write_service_accounts
meridian/generate.py        # + wire the three reference writers into generate()
meridian/kit_export.py      # NEW: CLI to export a quarter into the kit (no answer key)
tests/test_emit_reference.py        # NEW
tests/test_kit_export.py            # NEW
tests/test_coherence.py             # + assert reference JSONs present & new-app impl date in-quarter
```

**Part B — kit (`meridian-capstone` repo, created in Task 3):**
```
meridian-capstone/
  pyproject.toml              # pinned deps; registers the `api` pytest marker
  .gitignore
  data/2026-Q3/               # populated by kit_export in Task 6 (committed)
  contract/
    __init__.py
    findings.schema.json
    run_review.py             # stub: returns []
  mcp/
    __init__.py
    server.py                 # FastMCP server, 7 tools, over MERIDIAN_DATA_DIR
  examples/sample_findings.json
  tests/
    test_imports.py           # toolchain gate (Task 3)
    test_schema.py            # schema validates sample + empty (Task 4)
    test_contract.py          # run_review stub (Task 5)
    test_data.py              # data present & parseable (Task 6)
    test_mcp.py               # the 7 tools return correct data (Task 7)
    test_smoke.py             # aggregates the offline green light (Task 8)
    test_api.py               # mandatory live Claude call (Task 9)
  scripts/
    bootstrap.ps1             # Windows setup (Task 10)
    bootstrap.sh              # macOS/Linux fallback (Task 10)
  .mcp.json                   # (Task 10)
  .env.example                # (Task 10)
  CLAUDE.md                   # (Task 11)
  README.md                   # (Task 11)
```

---

## Part A — Generator prerequisite (repo: `claudecourse`)

### Task 1: Reference-JSON writers

**Repo:** `/Users/kev/dev/claudecourse`
**Files:**
- Modify: `meridian/emit.py`
- Test: `tests/test_emit_reference.py`

**Interfaces:**
- Consumes: `meridian.models.World`/`App`, `meridian.app_selection.effective_impl_date`, `meridian.models.AppSelection`.
- Produces:
  - `write_applications(path: str, world, selection, quarter_start: date) -> None` — writes a JSON array of app records, each `{name, tier, roles, privileged_roles, owning_dept, implementation_date}` where `implementation_date` is the **effective per-quarter** ISO date (`effective_impl_date(name, selection, world, quarter_start).isoformat()` — in-quarter for the new app).
  - `write_sod_matrix(path: str, world) -> None` — writes `{"conflicts": world.sod_conflicts, "exemptions": world.sod_exemptions}`.
  - `write_service_accounts(path: str, world) -> None` — writes the registry as a JSON array of strings.

- [ ] **Step 1: Write the failing test** in `tests/test_emit_reference.py`

```python
import json
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng
from meridian.app_selection import choose_apps
from meridian.emit import write_applications, write_sod_matrix, write_service_accounts


def _world_and_selection(seed=20260715):
    w = load_world("world")
    sel = choose_apps(w, make_rng(seed))
    return w, sel


def test_applications_has_all_apps_and_new_app_is_in_quarter(tmp_path):
    w, sel = _world_and_selection()
    q_start = date(2026, 7, 1)
    path = tmp_path / "applications.json"
    write_applications(str(path), w, sel, q_start)
    apps = json.load(open(path))
    assert len(apps) == len(w.apps) == 22
    by_name = {a["name"]: a for a in apps}
    # every record has the required fields
    for a in apps:
        assert set(a) == {"name", "tier", "roles", "privileged_roles",
                          "owning_dept", "implementation_date"}
    # the new app's effective implementation_date is inside the quarter
    new_date = date.fromisoformat(by_name[sel.new_app]["implementation_date"])
    assert new_date >= q_start


def test_sod_matrix_shape(tmp_path):
    w, _sel = _world_and_selection()
    path = tmp_path / "sod_matrix.json"
    write_sod_matrix(str(path), w)
    data = json.load(open(path))
    assert set(data) == {"conflicts", "exemptions"}
    assert any(e.get("clause") == "ACP-4.2" for e in data["exemptions"])


def test_service_accounts_is_list_with_known_members(tmp_path):
    w, _sel = _world_and_selection()
    path = tmp_path / "service_accounts.json"
    write_service_accounts(str(path), w)
    data = json.load(open(path))
    assert isinstance(data, list)
    assert "marcus.pipeline" in data and "emergency.admin" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_emit_reference.py -v`
Expected: FAIL with `ImportError` for the new `write_*` names.

- [ ] **Step 3: Add the writers to `meridian/emit.py`** (append after `copy_policies`)

```python
def write_applications(path: str, world, selection, quarter_start) -> None:
    from meridian.app_selection import effective_impl_date
    records = []
    for name, app in world.apps.items():
        eff = effective_impl_date(name, selection, world, quarter_start)
        records.append({
            "name": name,
            "tier": app.tier,
            "roles": list(app.roles),
            "privileged_roles": list(app.privileged_roles),
            "owning_dept": app.owning_dept,
            "implementation_date": eff.isoformat(),
        })
    with open(path, "w") as f:
        json.dump(records, f, indent=2)


def write_sod_matrix(path: str, world) -> None:
    with open(path, "w") as f:
        json.dump({"conflicts": world.sod_conflicts,
                   "exemptions": world.sod_exemptions}, f, indent=2)


def write_service_accounts(path: str, world) -> None:
    with open(path, "w") as f:
        json.dump(list(world.service_accounts), f, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_emit_reference.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/emit.py tests/test_emit_reference.py
git commit -m "feat: emit applications/sod_matrix/service_accounts reference JSON"
```

---

### Task 2: Wire reference emit into generate() + kit_export CLI

**Repo:** `/Users/kev/dev/claudecourse`
**Files:**
- Modify: `meridian/generate.py`
- Create: `meridian/kit_export.py`
- Modify: `tests/test_coherence.py` (add reference-file assertions)
- Test: `tests/test_kit_export.py`

**Interfaces:**
- Consumes: `meridian.generate.generate`, the Task 1 writers.
- Produces:
  - `generate(...)` additionally writes `applications.json`, `sod_matrix.json`, `service_accounts.json` into `out_dir`.
  - `meridian.kit_export.kit_export(seed: int, quarter: str, kit_dir: str) -> None` — generates the quarter into `<kit_dir>/data/<quarter>/` with `key_path=None` (answer key deliberately not written).
  - `python -m meridian.kit_export --seed <S> --quarter <Q> --kit-dir <path>` CLI.

- [ ] **Step 1: Write the failing test** in `tests/test_kit_export.py`

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_kit_export.py -v`
Expected: FAIL with `ModuleNotFoundError: meridian.kit_export`.

- [ ] **Step 3: Wire reference writers into `meridian/generate.py`**

Add the import at the top (extend the existing `from meridian.emit import ...`):

```python
from meridian.emit import (copy_policies, write_applications, write_entitlements,
                           write_hr_roster, write_prior_review, write_service_accounts,
                           write_sod_matrix, write_tickets)
```

Then, immediately after the existing `copy_policies(...)` line in `generate()`:

```python
    write_applications(os.path.join(out_dir, "applications.json"), world, selection, q_start)
    write_sod_matrix(os.path.join(out_dir, "sod_matrix.json"), world)
    write_service_accounts(os.path.join(out_dir, "service_accounts.json"), world)
```

- [ ] **Step 4: Create `meridian/kit_export.py`**

```python
from __future__ import annotations

import argparse
import os

from meridian.generate import generate


def kit_export(seed: int, quarter: str, kit_dir: str) -> None:
    """Generate a quarter's data into the kit, WITHOUT the answer key."""
    out_dir = os.path.join(kit_dir, "data", quarter)
    generate(seed, quarter, out_dir, key_path=None)  # key intentionally omitted


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="meridian.kit_export")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--quarter", required=True)
    ap.add_argument("--kit-dir", required=True)
    args = ap.parse_args(argv)
    kit_export(args.seed, args.quarter, args.kit_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add reference-file assertions to `tests/test_coherence.py`**

Append this test to `tests/test_coherence.py`:

```python
def test_generate_emits_self_contained_reference_files(tmp_path):
    import json
    from datetime import date
    from meridian.generate import generate, quarter_bounds
    out = tmp_path / "2026-Q3"
    generate(20260715, "2026-Q3", str(out), None)
    apps = json.load(open(out / "applications.json"))
    assert len(apps) == 22
    q_start, _ = quarter_bounds("2026-Q3")
    # at least one app (the new app) is implemented inside the quarter
    in_quarter = [a for a in apps
                  if date.fromisoformat(a["implementation_date"]) >= q_start]
    assert len(in_quarter) >= 1
    assert (out / "sod_matrix.json").exists()
    assert (out / "service_accounts.json").exists()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_kit_export.py tests/test_coherence.py -v`
Expected: PASS (kit-export test + coherence suite green, including the new reference-file test).

- [ ] **Step 7: Run the full generator suite (no regressions)**

Run: `pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add meridian/generate.py meridian/kit_export.py tests/test_kit_export.py tests/test_coherence.py
git commit -m "feat: self-contained exports + kit_export CLI (no answer key)"
```

---

## Part B — The kit (repo: `meridian-capstone`)

### Task 3: Kit scaffold + toolchain verification gate

**Repo:** `/Users/kev/dev/meridian-capstone` (created here)
**Files:**
- Create: `pyproject.toml`, `.gitignore`, `tests/test_imports.py`, package `__init__.py` files.

**Interfaces:**
- Produces: an installed kit environment (`pip install -e ".[dev]"`) with `claude_agent_sdk.query` and `mcp.server.fastmcp.FastMCP` importable. This task is the single place the SDK/MCP drift is caught.

- [ ] **Step 1: Initialize the repo and package layout**

```bash
mkdir -p /Users/kev/dev/meridian-capstone
cd /Users/kev/dev/meridian-capstone
git init
mkdir -p contract mcp tests examples scripts data
touch contract/__init__.py mcp/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "meridian-capstone"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "claude-agent-sdk>=0.1.59",
    "mcp>=1.2",
    "jsonschema>=4.21",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["contract*", "mcp*"]

[tool.pytest.ini_options]
markers = ["api: makes a real Claude API call (costs tokens); excluded by -m 'not api'"]
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
.env
```

- [ ] **Step 4: Write the toolchain-verification test** `tests/test_imports.py`

```python
def test_agent_sdk_query_importable():
    from claude_agent_sdk import query  # noqa: F401


def test_mcp_fastmcp_importable():
    # Official MCP SDK path. If this ever moves, the documented fallback is the
    # standalone `fastmcp` package (`from fastmcp import FastMCP`); update the
    # pin and mcp/server.py import together, and record the change here.
    from mcp.server.fastmcp import FastMCP  # noqa: F401


def test_jsonschema_importable():
    import jsonschema  # noqa: F401
```

- [ ] **Step 5: Install and run the gate**

Run:
```bash
cd /Users/kev/dev/meridian-capstone
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_imports.py -v
```
Expected: 3 passed. If `from mcp.server.fastmcp import FastMCP` fails, resolve per the fallback note (switch pin to `fastmcp` and adjust the import in `mcp/server.py` when you write it), then re-run until green. After install, pin the resolved versions exactly in `pyproject.toml` (replace `>=` with `==<installed>` for `claude-agent-sdk`, `mcp`, `jsonschema`, `pytest`) and note them in the commit.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore tests/test_imports.py contract/__init__.py mcp/__init__.py
git commit -m "chore: kit scaffold and toolchain verification gate"
```

---

### Task 4: The findings JSON Schema

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `contract/findings.schema.json`, `examples/sample_findings.json`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces: `contract/findings.schema.json` — a JSON Schema for a **list** of findings, each an account- or application-scoped object per spec. `examples/sample_findings.json` — a one-element list validating against it.

- [ ] **Step 1: Write the failing test** `tests/test_schema.py`

```python
import json
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.load(open(ROOT / "contract" / "findings.schema.json"))


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL (schema/sample files missing).

- [ ] **Step 3: Write `contract/findings.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Meridian UAR findings",
  "type": "array",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["scope", "account_id", "employee_id", "app", "entitlement",
                 "category", "severity", "recommendation", "rationale",
                 "evidence", "policy_citations", "confidence"],
    "properties": {
      "scope": {"enum": ["account", "application"]},
      "account_id": {"type": ["string", "null"]},
      "employee_id": {"type": ["string", "null"]},
      "app": {"type": "string"},
      "entitlement": {"type": ["string", "null"]},
      "category": {"enum": ["terminated_access", "orphan_account", "no_approval",
                            "grant_before_hire", "dormant_privileged",
                            "contractor_overstay", "privilege_creep",
                            "sod_conflict", "coverage_gap", "other"]},
      "severity": {"enum": ["critical", "high", "medium", "low"]},
      "recommendation": {"enum": ["revoke", "review", "retain"]},
      "rationale": {"type": "string", "minLength": 1},
      "evidence": {
        "type": "array", "minItems": 1,
        "items": {
          "type": "object", "additionalProperties": false,
          "required": ["source", "detail"],
          "properties": {"source": {"type": "string"}, "detail": {"type": "string"}}
        }
      },
      "policy_citations": {"type": "array", "items": {"type": "string"}},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "allOf": [
      {
        "if": {"properties": {"scope": {"const": "account"}}},
        "then": {"properties": {"account_id": {"type": "string"}}}
      },
      {
        "if": {"properties": {"scope": {"const": "application"}}},
        "then": {"properties": {"account_id": {"type": "null"},
                                "employee_id": {"type": "null"},
                                "entitlement": {"type": "null"}}}
      }
    ]
  }
}
```

- [ ] **Step 4: Write `examples/sample_findings.json`**

```json
[
  {
    "scope": "account",
    "account_id": "A004217",
    "employee_id": "E00918",
    "app": "Active Directory",
    "entitlement": "Domain Admin",
    "category": "terminated_access",
    "severity": "critical",
    "recommendation": "revoke",
    "rationale": "Employee terminated 2026-06-15; Domain Admin remains active with no revocation ticket.",
    "evidence": [
      {"source": "hr_roster", "detail": "term_date=2026-06-15, status=terminated"},
      {"source": "entitlements", "detail": "AD/Domain Admin, last_login 2026-06-10, still present"}
    ],
    "policy_citations": ["TERM-1"],
    "confidence": 0.98
  },
  {
    "scope": "application",
    "account_id": null,
    "employee_id": null,
    "app": "Box",
    "entitlement": null,
    "category": "coverage_gap",
    "severity": "medium",
    "recommendation": "review",
    "rationale": "Box holds live entitlements but was absent from the Q2 review and was implemented in 2016 — a genuine coverage gap, not a new rollout.",
    "evidence": [
      {"source": "prior_review", "detail": "no Box rows in prior_review"},
      {"source": "applications", "detail": "Box implementation_date=2016-05-01"}
    ],
    "policy_citations": ["ACP-1"],
    "confidence": 0.7
  }
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_schema.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add contract/findings.schema.json examples/sample_findings.json tests/test_schema.py
git commit -m "feat: frozen findings JSON Schema + sample"
```

---

### Task 5: The run_review contract stub

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `contract/run_review.py`
- Test: `tests/test_contract.py`

**Interfaces:**
- Produces: `contract.run_review.run_review(export_dir: Path, limit: int | None = None) -> list[dict]` returning `[]` (the stub). A `python -m contract.run_review <export_dir>` CLI printing findings as JSON.

- [ ] **Step 1: Write the failing test** `tests/test_contract.py`

```python
import json
from pathlib import Path
import jsonschema
from contract.run_review import run_review

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.load(open(ROOT / "contract" / "findings.schema.json"))


def test_stub_returns_empty_list():
    result = run_review(ROOT / "data" / "2026-Q3")
    assert result == []


def test_stub_output_validates_against_schema():
    jsonschema.validate(run_review(ROOT / "data" / "2026-Q3"), SCHEMA)


def test_accepts_limit_kwarg():
    assert run_review(ROOT / "data" / "2026-Q3", limit=5) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_contract.py -v`
Expected: FAIL with `ModuleNotFoundError` for `contract.run_review`.

- [ ] **Step 3: Write `contract/run_review.py`**

```python
"""The frozen capstone contract. The instructor's grader imports run_review and
calls it as run_review(export_dir, limit=None). Keep this signature exact.

You implement the body across Modules 1-6. It must return a list of findings,
each conforming to contract/findings.schema.json. `limit` caps how many
candidates reach the agent layer, for cheap iteration; None means the full run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_review(export_dir: Path, limit: int | None = None) -> list[dict]:
    export_dir = Path(export_dir)
    # TODO(you): build the Ledger, the agents, and the evidence writer here.
    # Return findings conforming to contract/findings.schema.json.
    return []


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="contract.run_review")
    ap.add_argument("export_dir")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    findings = run_review(Path(args.export_dir), limit=args.limit)
    json.dump(findings, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
```

(The `TODO(you)` is deliberate learner-facing scaffolding — the one place a TODO is the intended deliverable, not a plan gap.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_contract.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add contract/run_review.py tests/test_contract.py
git commit -m "feat: frozen run_review contract stub + CLI"
```

---

### Task 6: Populate the kit's Q3 data

**Repo:** `/Users/kev/dev/meridian-capstone` (data generated by the `claudecourse` generator)
**Files:**
- Create: `data/2026-Q3/*` (generated, committed)
- Test: `tests/test_data.py`

**Interfaces:**
- Consumes: `meridian.kit_export` (Part A, Task 2).
- Produces: the committed `data/2026-Q3/` export (no answer key).

- [ ] **Step 1: Write the failing test** `tests/test_data.py`

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/kev/dev/meridian-capstone && pytest tests/test_data.py -v`
Expected: FAIL (data dir empty).

- [ ] **Step 3: Generate the data via the generator's kit_export**

From the generator repo, export into the kit (this writes the export, never the key):
```bash
cd /Users/kev/dev/claudecourse
python -m meridian.kit_export --seed 20260715 --quarter 2026-Q3 --kit-dir /Users/kev/dev/meridian-capstone
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/kev/dev/meridian-capstone && pytest tests/test_data.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit the data + test**

```bash
cd /Users/kev/dev/meridian-capstone
git add data/2026-Q3 tests/test_data.py
git commit -m "data: ship generated Q3 export (no answer key)"
```

---

### Task 7: The Meridian systems MCP server

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `mcp/server.py`
- Test: `tests/test_mcp.py`

**Interfaces:**
- Produces: seven read-only tools over `MERIDIAN_DATA_DIR` (default `data/2026-Q3`). Data-access logic lives in plain `_impl(data_dir, ...)` functions (testable directly); thin `@mcp.tool()` wrappers call them with the env-configured dir. `mcp.run()` serves stdio under `if __name__ == "__main__"`.
- Tools: `get_employee(employee_id)`, `get_account(account_id)`, `search_tickets(account_id, app=None)`, `get_prior_review(account_id)`, `get_application(app_name)`, `is_approved_service_account(name)`, `get_sod_matrix()`.

- [ ] **Step 1: Write the failing test** `tests/test_mcp.py` (targets the plain `_impl` functions with an explicit data dir)

```python
import csv
from pathlib import Path
from mcp import server as srv

DATA = Path(__file__).resolve().parent.parent / "data" / "2026-Q3"


def _any_employee_id():
    return next(csv.DictReader(open(DATA / "hr_roster.csv")))["employee_id"]


def _any_account_id():
    return next(csv.DictReader(open(DATA / "entitlements.csv")))["account_id"]


def test_get_employee_known_and_unknown():
    emp = _any_employee_id()
    rec = srv._get_employee(DATA, emp)
    assert rec is not None and rec["employee_id"] == emp
    assert srv._get_employee(DATA, "E999999") is None


def test_get_account_returns_entitlements():
    acct = _any_account_id()
    rec = srv._get_account(DATA, acct)
    assert rec is not None
    assert rec["account_id"] == acct
    assert isinstance(rec["entitlements"], list) and rec["entitlements"]


def test_get_application_has_implementation_date():
    app = srv._get_application(DATA, "Atlas ERP")
    assert app is not None and "implementation_date" in app
    assert srv._get_application(DATA, "Nonexistent App") is None


def test_service_account_registry_check():
    assert srv._is_approved_service_account(DATA, "marcus.pipeline") is True
    assert srv._is_approved_service_account(DATA, "definitely.not.a.svc") is False


def test_sod_matrix_has_conflicts_and_exemption():
    m = srv._get_sod_matrix(DATA)
    assert m["conflicts"] and any(e.get("clause") == "ACP-4.2" for e in m["exemptions"])


def test_search_tickets_by_account():
    # find an account that actually has a ticket
    import json
    tickets = json.load(open(DATA / "access_tickets.json"))
    if tickets:
        acct = tickets[0]["account_id"]
        found = srv._search_tickets(DATA, acct)
        assert any(t["account_id"] == acct for t in found)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp.py -v`
Expected: FAIL with `ImportError`/`AttributeError` (no `mcp/server.py` impl functions).

- [ ] **Step 3: Write `mcp/server.py`**

```python
"""Meridian systems MCP server (read-only).

Course simplification: a real client would expose HR, identity, and ITSM as
separate connectors; this collapses them into one server for setup simplicity.
Configure the data directory via MERIDIAN_DATA_DIR (default data/2026-Q3).
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def data_dir() -> Path:
    return Path(os.environ.get("MERIDIAN_DATA_DIR", "data/2026-Q3"))


def _read_csv(d: Path, name: str) -> list[dict]:
    with open(d / name, newline="") as f:
        return list(csv.DictReader(f))


def _read_json(d: Path, name: str):
    with open(d / name) as f:
        return json.load(f)


# --- plain implementations (directly unit-tested) ---

def _get_employee(d: Path, employee_id: str) -> dict | None:
    for row in _read_csv(d, "hr_roster.csv"):
        if row["employee_id"] == employee_id:
            return row
    return None


def _get_account(d: Path, account_id: str) -> dict | None:
    ents = [r for r in _read_csv(d, "entitlements.csv") if r["account_id"] == account_id]
    if not ents:
        return None
    return {"account_id": account_id,
            "account_name": ents[0]["account_name"],
            "entitlements": [{k: r[k] for k in
                              ("app", "role", "granted_date", "granted_by", "last_login")}
                             for r in ents]}


def _search_tickets(d: Path, account_id: str, app: str | None = None) -> list[dict]:
    out = [t for t in _read_json(d, "access_tickets.json")
           if t["account_id"] == account_id and (app is None or t["app"] == app)]
    return out


def _get_prior_review(d: Path, account_id: str) -> list[dict]:
    return [r for r in _read_csv(d, "prior_review.csv") if r["account_id"] == account_id]


def _get_application(d: Path, app_name: str) -> dict | None:
    for a in _read_json(d, "applications.json"):
        if a["name"] == app_name:
            return a
    return None


def _is_approved_service_account(d: Path, name: str) -> bool:
    return name in _read_json(d, "service_accounts.json")


def _get_sod_matrix(d: Path) -> dict:
    return _read_json(d, "sod_matrix.json")


# --- MCP tool wrappers (thin; use the env-configured data dir) ---

mcp = FastMCP("meridian-systems")


@mcp.tool()
def get_employee(employee_id: str) -> dict | None:
    """HR record for an employee, or null if none exists (the orphan signal)."""
    return _get_employee(data_dir(), employee_id)


@mcp.tool()
def get_account(account_id: str) -> dict | None:
    """IAM view of one account: account_name and its entitlement rows."""
    return _get_account(data_dir(), account_id)


@mcp.tool()
def search_tickets(account_id: str, app: str | None = None) -> list:
    """Access-request tickets for an account, optionally filtered by app."""
    return _search_tickets(data_dir(), account_id, app)


@mcp.tool()
def get_prior_review(account_id: str) -> list:
    """Last quarter's review decisions for an account (empty if none)."""
    return _get_prior_review(data_dir(), account_id)


@mcp.tool()
def get_application(app_name: str) -> dict | None:
    """App catalog entry: tier, implementation_date, roles, privileged_roles, owning_dept."""
    return _get_application(data_dir(), app_name)


@mcp.tool()
def is_approved_service_account(name: str) -> bool:
    """True if the account name is in the approved service-account registry."""
    return _is_approved_service_account(data_dir(), name)


@mcp.tool()
def get_sod_matrix() -> dict:
    """Structured SoD conflict pairs and documented exemptions."""
    return _get_sod_matrix(data_dir())


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add mcp/server.py tests/test_mcp.py
git commit -m "feat: Meridian systems MCP server (7 read-only tools)"
```

---

### Task 8: The offline smoke test

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `tests/test_smoke.py`

**Interfaces:**
- Produces: `tests/test_smoke.py` — the aggregate offline green light (data loads, contract wires, MCP answers). No API call here; it must pass under `pytest -m "not api"`.

- [ ] **Step 1: Write the test** `tests/test_smoke.py`

```python
"""Offline green light: data + contract + MCP. Free, deterministic, CI-able.
Run with `pytest -m "not api"` to skip the paid API check in test_api.py."""
import json
from pathlib import Path

import jsonschema

from contract.run_review import run_review
from mcp import server as srv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "2026-Q3"
SCHEMA = json.load(open(ROOT / "contract" / "findings.schema.json"))


def test_data_directory_is_complete():
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv", "applications.json", "sod_matrix.json",
                 "service_accounts.json"]:
        assert (DATA / name).exists(), name


def test_contract_runs_and_validates():
    findings = run_review(DATA)
    assert isinstance(findings, list)
    jsonschema.validate(findings, SCHEMA)
    jsonschema.validate(json.load(open(ROOT / "examples" / "sample_findings.json")), SCHEMA)


def test_mcp_tools_answer():
    apps = srv._get_application(DATA, "Atlas ERP")
    assert apps and "implementation_date" in apps
    import csv
    emp = next(csv.DictReader(open(DATA / "hr_roster.csv")))["employee_id"]
    assert srv._get_employee(DATA, emp) is not None
```

- [ ] **Step 2: Run the offline subset**

Run: `pytest -m "not api" -v`
Expected: PASS — all non-api tests (imports, schema, contract, data, mcp, smoke) green.

- [ ] **Step 3: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: offline green light (data + contract + MCP)"
```

---

### Task 9: The mandatory live-API check

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `tests/test_api.py`

**Interfaces:**
- Produces: `tests/test_api.py::test_claude_api_responds`, marked `@pytest.mark.api` — one real `claude_agent_sdk.query` call; part of the full `pytest` green light, excluded by `-m "not api"`.

- [ ] **Step 1: Write the test** `tests/test_api.py`

```python
"""Mandatory live-API green light: proves ANTHROPIC_API_KEY + billing work.
One real Claude call. Marked `api` so `pytest -m "not api"` skips it for CI.

Note: the Agent SDK does NOT auto-load .env; the key must be in the environment
(the bootstrap exports it, or use `python-dotenv`/`set` before running)."""
import asyncio
import os

import pytest

from claude_agent_sdk import query


def _collect_text() -> str:
    async def run():
        chunks = []
        async for message in query(prompt="Reply with the exact word: READY"):
            content = getattr(message, "content", None)
            if content:
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        chunks.append(text)
        return "".join(chunks)
    return asyncio.run(run())


@pytest.mark.api
def test_claude_api_responds():
    assert os.environ.get("ANTHROPIC_API_KEY"), \
        "ANTHROPIC_API_KEY not set — copy .env.example to .env and add your key, " \
        "then export it into the environment before running the API check."
    out = _collect_text()
    assert out.strip(), "no text returned from Claude — check key, billing, and network"
```

- [ ] **Step 2: Verify the marker split works (offline)**

Run: `pytest -m "not api" -q`
Expected: PASS, and the api test is deselected (shown as deselected, not run).

- [ ] **Step 3: Run the full green light (requires a real key + billing)**

Run: `export ANTHROPIC_API_KEY=sk-... && pytest -q`
Expected: all pass including `test_claude_api_responds`. If no key is available on the build machine, run `pytest -m "not api" -q` (green) and record that the API test was verified separately / is pending a keyed run — do NOT weaken or delete the test.

- [ ] **Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "test: mandatory live-Claude API green light (marked api)"
```

---

### Task 10: Windows bootstrap + env config

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`, `.mcp.json`, `.env.example`

**Interfaces:**
- Produces: a one-command Windows setup that checks/installs prerequisites via winget, wires Claude Code + venv + VS Code extensions + `.env`, then runs the green light. `.mcp.json` registers the server for Claude Code/VS Code.

- [ ] **Step 1: Write `.env.example`**

```
ANTHROPIC_API_KEY=
```

- [ ] **Step 2: Write `.mcp.json`**

```json
{
  "mcpServers": {
    "meridian-systems": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp.server"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MERIDIAN_DATA_DIR": "data/2026-Q3"
      }
    }
  }
}
```

- [ ] **Step 3: Write `scripts/bootstrap.ps1`**

```powershell
#Requires -Version 5.1
# Meridian capstone — Windows setup. Idempotent: checks each prerequisite and
# installs only what's missing via winget, then wires the project and runs the
# green light. Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
$ErrorActionPreference = "Stop"

function Ensure-WingetPackage($Id, $Name) {
    winget list --id $Id -e *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[ok] $Name already installed"
    } else {
        Write-Host "[..] installing $Name ($Id)"
        winget install -e --id $Id --silent --accept-package-agreements --accept-source-agreements --no-upgrade
        if ($LASTEXITCODE -ne 0) { throw "winget failed to install $Name ($Id)" }
        Write-Host "[ok] installed $Name"
    }
}

Write-Host "== Meridian capstone setup =="

# 1. Prerequisites (verified winget ids)
Ensure-WingetPackage "Python.Python.3.12"        "Python 3.12"
Ensure-WingetPackage "Git.Git"                   "Git"
Ensure-WingetPackage "OpenJS.NodeJS.LTS"         "Node.js LTS"
Ensure-WingetPackage "Microsoft.VisualStudioCode" "VS Code"

# refresh PATH so freshly installed tools are visible in this session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

# 2. Claude Code (ships over npm; needs Node)
Write-Host "[..] installing Claude Code (npm)"
npm install -g "@anthropic-ai/claude-code"

# 3. Python project (venv + pinned deps)
Write-Host "[..] creating venv and installing deps"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 4. VS Code extensions
Write-Host "[..] installing VS Code extensions"
code --install-extension ms-python.python --force
code --install-extension anthropic.claude-code --force

# 5. .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[!!] Created .env — open it and paste your ANTHROPIC_API_KEY, then re-run to complete the API check."
}

# 6. Green light
Write-Host "== running green light (pytest) =="
if ((Get-Content ".env" | Where-Object { $_ -match "^ANTHROPIC_API_KEY=.+" })) {
    $key = ((Get-Content ".env" | Where-Object { $_ -match "^ANTHROPIC_API_KEY=" }) -replace "^ANTHROPIC_API_KEY=","").Trim()
    $env:ANTHROPIC_API_KEY = $key
    .\.venv\Scripts\python.exe -m pytest -q
    Write-Host "== READY: environment green (including live API) =="
} else {
    .\.venv\Scripts\python.exe -m pytest -m "not api" -q
    Write-Host "== Offline checks green. Add your ANTHROPIC_API_KEY to .env and re-run for the mandatory API check. =="
}
```

- [ ] **Step 4: Write `scripts/bootstrap.sh`** (secondary macOS/Linux fallback)

```bash
#!/usr/bin/env bash
# Secondary fallback for macOS/Linux. Windows (bootstrap.ps1) is the supported path.
set -euo pipefail
command -v python3 >/dev/null || { echo "install Python 3.11+ first"; exit 1; }
command -v git >/dev/null || { echo "install Git first"; exit 1; }
command -v node >/dev/null || { echo "install Node LTS first"; exit 1; }
npm install -g @anthropic-ai/claude-code || true
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
[ -f .env ] || cp .env.example .env
if grep -q '^ANTHROPIC_API_KEY=.\+' .env; then
  export ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)"
  ./.venv/bin/python -m pytest -q
  echo "== READY: environment green (including live API) =="
else
  ./.venv/bin/python -m pytest -m "not api" -q
  echo "== Offline checks green. Add ANTHROPIC_API_KEY to .env and re-run. =="
fi
```

- [ ] **Step 5: Syntax-check what the build machine can, review the rest**

Run (if PowerShell Core is available on the build machine):
```bash
pwsh -NoProfile -Command "\$null = [System.Management.Automation.Language.Parser]::ParseFile('scripts/bootstrap.ps1', [ref]\$null, [ref]\$errs); if (\$errs) { \$errs; exit 1 } else { 'ps1 syntax ok' }"
bash -n scripts/bootstrap.sh && echo "sh syntax ok"
```
Expected: both report ok. If `pwsh` is not installed, record that `bootstrap.ps1` passed structural review against the verified winget commands and must get one real run on a Windows box by the instructor before the cohort uses it (the winget/npm/code calls cannot execute on macOS). `bash -n` on the fallback must pass regardless.

- [ ] **Step 6: Commit**

```bash
git add scripts/bootstrap.ps1 scripts/bootstrap.sh .mcp.json .env.example
git commit -m "feat: Windows-first bootstrap + MCP/env config"
```

---

### Task 11: CLAUDE.md + README

**Repo:** `/Users/kev/dev/meridian-capstone`
**Files:**
- Create: `CLAUDE.md`, `README.md`

**Interfaces:**
- Produces: the learner-facing onboarding and Claude Code project memory. No code; verification is a content checklist.

- [ ] **Step 1: Write `CLAUDE.md`**

```markdown
# Meridian Capstone — project memory

You are helping build an agentic user-access-review (UAR) system for the
fictional utility **Meridian Regional Energy**, on top of a fixed data set.

## The frozen contract — do not change its shape
`contract/run_review.py` exposes `run_review(export_dir: Path, limit: int | None = None) -> list[dict]`.
The instructor's grader imports and calls this exact signature. Every finding
you return must validate against `contract/findings.schema.json`. `limit` caps
how many candidates reach the agent layer — use it for cheap iteration while
debugging; grading calls with `limit=None`. Produce `findings.json` with
`python -m contract.run_review data/2026-Q3 > findings.json` and submit that.

## The data (`data/2026-Q3/`)
Raw exports from Meridian's systems — messy on purpose (name mismatches, mixed
date formats, a few duplicate rows). Read them **in bulk** for the deterministic
Ledger join. The five `policies/*.md` become Agent Skills in Module 2.

## The MCP server (`mcp/server.py`)
Read-only, per-entity lookups over Meridian's systems: `get_employee`,
`get_account`, `search_tickets`, `get_prior_review`, `get_application`,
`is_approved_service_account`, `get_sod_matrix`. Use these for **targeted,
judgment-time** lookups about one account/person — not for bulk data (that's the
Ledger, from files). **Course simplification:** a real client would have these as
separate connectors (Workday/Okta/ServiceNow); this collapses them into one
server. Carry that caveat into real engagements.

## Rules of the road
- Honor the contract signature exactly.
- Reconciliation is code (files); judgment is agents (MCP).
- `make check` doesn't exist here — the green light is `pytest` (offline subset:
  `pytest -m "not api"`).
```

- [ ] **Step 2: Write `README.md`**

```markdown
# Meridian Capstone Kit

Your starting point for the Claude Certified Architect capstone: build an
agentic user-access-review system for Meridian Regional Energy.

## Setup (Windows — 10 minutes)
1. Clone this repo and open a PowerShell prompt in it.
2. Run: `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1`
   It checks for and installs Python, Git, Node, and VS Code (via winget),
   installs Claude Code, creates the Python environment, and runs the checks.
3. When prompted, open `.env` and paste your `ANTHROPIC_API_KEY`, then re-run
   the bootstrap to complete the **mandatory** API check.
4. Green light: `pytest` passes end to end (including one live Claude call).

macOS/Linux: use `scripts/bootstrap.sh` (secondary; Windows is supported).

## What's here
- `data/2026-Q3/` — the access data + reference files you review.
- `contract/` — the frozen `run_review` contract and the findings JSON Schema.
- `mcp/server.py` — Meridian's systems as a read-only MCP server.
- `examples/sample_findings.json` — a valid finding, for shape reference.

## What you do
Implement `run_review` across Modules 1–6, run it to produce `findings.json`
(`python -m contract.run_review data/2026-Q3 > findings.json`), and submit that
for grading. You will not receive an answer key — your submitted output is graded.

## Checks
- Full green light (includes a paid API call): `pytest`
- Offline subset (free, for iteration): `pytest -m "not api"`
```

- [ ] **Step 3: Content checklist (verification)**

Confirm by reading both files:
- `CLAUDE.md` states the exact contract signature, the reconciliation-vs-judgment rule, and the single-server course-simplification caveat.
- `README.md` leads with the Windows bootstrap, names the mandatory API check, and states learners get no answer key and submit their output.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: CLAUDE.md project memory + README onboarding"
```

---

## Self-Review Notes

- **Spec coverage:** kit boundary/no-key (Tasks 2, 6 + `test_no_answer_key_shipped`), repo structure (all tasks), frozen contract + schema (Tasks 4, 5), the 7 MCP tools incl. `implementation_date` for coverage-gap (Task 7), generator prerequisite / self-contained export (Tasks 1, 2), mandatory API green light + offline subset (Tasks 8, 9), Windows-first winget bootstrap incl. Node rationale (Task 10), CLAUDE.md/README with the single-server caveat (Task 11). Every spec section maps to a task.
- **Cross-repo ordering:** Tasks 1–2 (generator) must complete before Task 6 (which runs `kit_export`). Tasks 3–5 (kit scaffold/schema/contract) don't depend on the data and can precede it; 7–9 depend on Task 6's data. The subagent-driven controller must run tasks in listed order and operate each in the repo named at its top.
- **Toolchain drift is quarantined to Task 3.** The one uncertain import (`mcp.server.fastmcp.FastMCP`) is asserted there before anything builds on it, with a documented `fastmcp`-package fallback; exact versions are pinned post-install.
- **Windows-only surface:** `bootstrap.ps1` cannot execute on the macOS build machine (winget/npm/code). It is authored against verified winget ids and syntax-checked; the plan explicitly defers one real Windows run to the instructor. Everything else (Python schema, contract, MCP server, all pytest) is cross-platform and fully verified here.
- **Intentional TODO:** the `TODO(you)` in `run_review.py` is learner scaffolding, the one place a TODO is the deliverable — not a plan gap.
- **API-test honesty:** if the build machine has no key, the plan runs `-m "not api"` and records the API test as pending a keyed run rather than weakening it.
