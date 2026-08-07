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

## Start here
Open `index.html` — a browsable portal that links all 39 sub-tasks and lets you
explore Meridian's world (policies, roster, entitlements, tickets, and a user
lookup). It works by double-clicking; for the two large tables, serve it with
`python -m http.server 8000` and open http://localhost:8000/index.html.

## What's here
- `index.html` — the course portal + world-data browser (above).
- `course/v2/` — the 39 sub-tasks, plus optional pre-work and skill survey.
- `data/2026-Q3/` — the access data + reference files you review.
- `src/meridian_capstone/contract/` — the frozen `run_review` contract and the findings JSON Schema.
- `src/meridian_capstone/mcp_server/server.py` — Meridian's systems as a read-only MCP server.
- `examples/sample_findings.json` — a valid finding, for shape reference.

## What you do
Implement `run_review` across the 39 sub-tasks, run it to produce `findings.json`
(`python -m meridian_capstone.contract.run_review data/2026-Q3 > findings.json`), and submit that
for grading. You will not receive an answer key — your submitted output is graded.

## Checks
- Full green light (includes a paid API call): `pytest`
- Offline subset (free, for iteration): `pytest -m "not api"`
