# Claude Certified Architect

The authoring repo for **Claude Certified Architect** — a course in which you build
one real agentic system and then prove it generalizes.

You take an automated **user-access review** for Meridian Regional Energy, a fictional
regional gas & electric utility, from a plain `CLAUDE.md` all the way up to a
self-checking orchestrator: reconcile messy exports into a trustworthy ledger, turn
five written compliance policies into Agent Skills, give the agent read-only reach
over MCP, split the work across subagents, wrap it in hooks that guard before and
audit after, evaluate it, cost it — then point the finished system at a quarter it has
never seen and show it holds.

The through-line is **intent-based development**: you describe what good looks like
and direct Claude Code to build it.

## Structure

**39 linear sub-tasks, ~42 hours.** One straight line — every sub-task states an
outcome you can check before moving on, and assumes the one before it is done and
green. Nine themes group them as signposts, not gates. The course is pacing-agnostic:
work it self-paced, or bundle it into days or weeks however suits your delivery.

### The six building blocks

Each block is marked with the sub-task where you *finish* it — the milestone, not the
introduction.

| # | Block | Artifact | Completed at |
|---|-------|----------|--------------|
| 1 | Rules | `CLAUDE.md` | sub-task 7 |
| 2 | Skills | `policies/*.md` | sub-task 17 |
| 3 | Tools | MCP server | sub-task 20 |
| 4 | Subagents | orchestrator + specialists | sub-task 23 |
| 5 | Hooks | `.claude/hooks/` | sub-task 26 |
| 6 | Generalization | `data/2026-Q4/` | sub-task 39 |

### The nine themes

| | Theme | Sub-tasks | Time |
|---|---|---|---|
| A | Foundations | 1–7 | ~6.75 h |
| B | Reconciliation is code | 8–12 | ~5.5 h |
| C | First agent | 13–15 | ~2.25 h |
| D | Skills | 16–19 | ~4.75 h |
| E | Tools | 20–22 | ~2.75 h |
| F | Subagents | 23–25 | ~4.25 h |
| G | Hooks + injection defense | 26–28 | ~2.75 h |
| H | Evals, HITL & tiering | 29–36 | ~8.75 h |
| I | Generalization | 37–39 | ~4 h |

## How to use it

Open **`index.html`** in a browser — that's the portal and the entry point. It links
every sub-task and includes a browser for Meridian's world data.

It works by double-clicking (`file://`): the policies, HR roster, tickets, user lookup
and reference files all load inline. The two large tables (entitlements, prior review)
are fetched on demand, so for those serve the repo instead:

```bash
python -m http.server 8000   # then open http://localhost:8000/index.html
```

## Layout

Course content (authoring repo):

```
index.html                    the portal — generated, the entry point
scripts/portal.template.html  the portal source; build with scripts/build_portal.py
course/v2/subtask-NN.html     the 39 sub-tasks
course/pre-work.html          optional pre-course setup
course/skill-survey.html      optional pre-course readiness survey
```

The kit students clone (lives at repo root so `pytest` and every course path resolves
without contortion):

```
CLAUDE.md          student-facing project rules
.mcp.json          meridian-systems MCP server wiring
.claude/           student Claude Code config (hook stubs under hooks/examples/)
.env.example       API-key template
data/2026-Q3/      the training quarter
data/2026-Q4/      the unseen transfer quarter (pre-generated, ships to students)
src/               meridian_capstone package — the frozen contract + MCP server
tests/             the green light
scripts/           bootstrap.sh / bootstrap.ps1
examples/          sample_findings.json
pyproject.toml     package + deps
README.student.md  the README the student repo ships as README.md
```

Answer material — never shipped to learners:

```
meridian/    the data generator (source + meridian/tests/)
world/       world YAMLs the generator reads
docs/        design specs and plans
```

## Running things

- **Student green light (offline subset):** `pytest -m "not api"`
- **Full green light (one paid Claude call):** `pytest` (needs `ANTHROPIC_API_KEY` in `.env`)
- **Generator tests (answer material):** `pytest meridian/tests`
- **Regenerate a quarter:** `python -m meridian.generate --seed <seed> --quarter <YYYY-Qn> --out data/<YYYY-Qn>`
  (needs `pip install -e ".[course-source,dev]"`)
- **Rebuild the portal:** `python scripts/build_portal.py` — run it after any edit to
  `scripts/portal.template.html` or the embedded data, and commit both files together.

Default `pytest` only collects `tests/` via `testpaths`, so the generator tests don't
inflate the student count.

## Producing the student repo

Clone this repo, then from the clone's root:

```bash
rm -rf meridian world docs      # answer material
mv README.student.md README.md  # swap in the student-facing README
# optional: drop the course-source extra from pyproject.toml
```

Both quarters of data ship pre-generated, so the generalization theme works without
the generator the strip removes.

## Ownership

Maintained by **kmcoleman**.
