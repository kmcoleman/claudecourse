# Meridian Capstone — project memory

You are helping build an agentic user-access-review (UAR) system for the
fictional utility **Meridian Regional Energy**, on top of a fixed data set.

## The frozen contract — do not change its shape
`src/meridian_capstone/contract/run_review.py` exposes `run_review(export_dir: Path, limit: int | None = None) -> list[dict]`.
The instructor's grader imports and calls this exact signature. Every finding
you return must validate against `src/meridian_capstone/contract/findings.schema.json`. `limit` caps
how many candidates reach the agent layer — use it for cheap iteration while
debugging; grading calls with `limit=None`. Produce `findings.json` with
`python -m meridian_capstone.contract.run_review data/2026-Q3 > findings.json` and submit that.

## The data (`data/2026-Q3/`)
Raw exports from Meridian's systems — messy on purpose (name mismatches, mixed
date formats, a few duplicate rows). Read them **in bulk** for the deterministic
Ledger join. The five `policies/*.md` become Agent Skills in Module 2.

## The MCP server (`src/meridian_capstone/mcp_server/server.py`)
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
