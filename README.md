# claudecourse — Meridian Capstone (working repo)

This is the **development / authoring** repo for the Claude Certified Architect
capstone. It holds two things in one tree:

1. **The student kit** — everything a learner clones and builds on (at repo root,
   so `pytest` and every course path resolve without contortion).
2. **The answer material** — the course HTML, the data generator, world design,
   and design docs the learner must never see.

The plan is to keep authoring here, then produce the **student-facing repo** by
cloning this one and deleting the answer-material directories (see *Stripping for
the student version* below). Nothing about the kit's layout depends on the answer
material being present, so that strip is a handful of `rm -rf`s.

## Layout

```
claudecourse/
├── .claude/        KIT  — student Claude Code config (hook stubs under hooks/examples/)
├── .mcp.json       KIT  — meridian-systems MCP server wiring (MERIDIAN_DATA_DIR=data/2026-Q3)
├── .env.example    KIT  — API-key template
├── CLAUDE.md       KIT  — student-facing project rules
├── index.html      KIT  — course portal + world-data browser
│                          (generated: `python scripts/build_portal.py`)
├── README.student.md  KIT — the README the student repo ships as README.md
├── pyproject.toml  KIT  — meridian_capstone package + deps (generator deps in the
│                          optional `course-source` extra)
├── data/
│   ├── 2026-Q3/    KIT  — committed course data (the quarter students review)
│   └── 2026-Q4/    KIT  — pre-generated Day 5 transfer quarter (committed; ships to students)
├── src/            KIT  — meridian_capstone package (contract + MCP server)
├── tests/          KIT  — the green light (`pytest -m "not api"`)
├── scripts/        KIT  — bootstrap.sh / bootstrap.ps1; build_portal.py
│                          (+ portal.template.html → index.html)
├── examples/       KIT  — sample_findings.json
│
├── course/         ANSWER — day-1..5 HTML
├── meridian/       ANSWER — data generator (source + meridian/tests/)
├── world/          ANSWER — world YAMLs the generator reads
└── docs/           ANSWER — design specs and plans
```

## Running things

- **Student green light (offline subset):** `pytest -m "not api"`
- **Full green light (one paid Claude call):** `pytest`  (needs `ANTHROPIC_API_KEY` in `.env`)
- **Generator tests (answer material):** `pytest meridian/tests`
- **Regenerate a quarter:** `python -m meridian.generate --seed <seed> --quarter <YYYY-Qn> --out data/<YYYY-Qn>`
  (needs the generator deps: `pip install -e ".[course-source,dev]"`)

Default `pytest` only collects `tests/` (the kit) via `testpaths`, so the
generator tests don't inflate the student count.

## Stripping for the student version (future)

Clone this repo, then from the clone's root:

```bash
rm -rf course meridian world docs      # answer material
mv README.student.md README.md          # swap in the student-facing README
# optional: drop the generator extra from pyproject.toml's [project.optional-dependencies]
```

What remains is the runnable student kit at root — including both quarters of
data. Q4 (`data/2026-Q4/`) ships pre-generated so Day 5's transfer lesson works
without the generator (which the strip removes); Cycle 1 has students *read*
the pre-shipped Q4, not create it. No Day 5 coupling to resolve before
publishing.
