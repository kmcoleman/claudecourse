# Module 5 — Evals: Effectiveness and Efficiency — Design

**Status:** draft for review · 28 July 2026
**Parent:** [Meridian UAR Capstone Program](./2026-07-15-uar-capstone-design.md)
**Depends on:** [Module 0 Setup Kit](./2026-07-22-module0-setup-kit-design.md) — learners never hold the answer key; Module 3's specialist architecture (orchestrator + termination/SoD/privilege-creep analysts + evidence writer, fanned across ~150 candidates)
**Position:** Week 9, the module immediately before generalization (Module 6). Formalizes the eval habit the weekly deliverable ("code in the repo, a decision log, the artifacts") has been building informally since Module 1.

---

## Purpose

Module 5 as originally sketched had learners "score against the labeled Q3 key." The Module 0 kit
design closed that off deliberately — learners never receive an answer key, so hard-coding to it is
impossible by construction (see that spec's *kit boundary*). Module 5 has to teach something a
learner can actually run without one: **building confidence in a system without ever seeing the
number it's truly graded on.**

That turns out to be two separate questions, and conflating them is the most common mistake this
module exists to prevent:

1. **Effectiveness** — is the system finding the right things, for defensible reasons?
2. **Efficiency** — is it doing that cheaply and quickly enough to actually run every quarter?

A system that nails catch rate and still costs $40 and 90 minutes per quarter on 1,200 employees is
not shippable to a two-person IAM team. A system that's blazing fast and still cries wolf on every
service account (a trap, see the parent spec's planted-findings section) is worse than no system.
Module 5 grades both — which is also why it now serves two exam domains, not one: **Context
Management & Reliability (15%)** for the effectiveness techniques, and a real slice of **Prompt
Engineering & Structured Output (20%)** for the efficiency ones, since cost and latency control *is*
prompt engineering once a prompt runs at production volume rather than in a REPL.

---

## Effectiveness evals — four techniques, cheap to expensive

| Technique | What it checks | Cost |
|---|---|---|
| Schema & coverage validation | Every finding conforms to `findings.schema.json`; the category distribution isn't degenerate (all `other`, zero criticals, one app eating every finding) | Free, deterministic |
| Self-consistency | Same export run twice — or with a paraphrased prompt — flags the same accounts at the same severity. Divergence means a prompt is underspecified, not that it found something new | One extra pipeline run |
| Hand-labeled micro-key | The learner reads 10–15 candidate dossiers themselves, writes their own verdict, and scores their system against *their own* labels — the one piece of ground truth they're allowed, because they built it | A few hours, once |
| Rationale rubric (LLM-as-judge) | A judge prompt scores each finding's rationale for being evidence-grounded and policy-cited — not whether the verdict is right (needs a key), but whether it's defensible (doesn't) | One judge call per finding |

The must-catch / judgment / traps tiers from the case study still exist and still matter — they're
what the grading agent scores against a freshly generated Q4 quarter. Module 5's own harness is
deliberately blind to that key; it answers a different, learnable question: **is this prompt's
output stable, well-formed, and defensible.**

This doubles as a regression test. Tuning an analyst's prompt in Module 3 and fixing an SoD false
positive while quietly breaking termination detection shows up against the micro-key immediately —
instead of at Module 6 generalization, where it's a much worse place to learn it.

---

## Efficiency evals — what to measure

Module 3's fan-out is the cost center: an orchestrator triaging ~150 candidates across two or three
specialists each is several hundred model calls per full run. Two measurements make that legible
instead of just "the API bill was bigger than expected."

| Metric | How | Why it matters |
|---|---|---|
| Cost per review | Sum `response.usage` (input, output, cache-write, cache-read tokens) across the whole `run_review()` call, at the model's per-token rate | The number the IAM team's manager actually asks about |
| Cost per finding | Cost per review ÷ number of findings surfaced | Catches "found 3 obvious things for $40" — a failure mode raw total cost hides |
| Wall-clock latency | Time `run_review()` end to end, and per-candidate average | A quarterly review that takes 6 hours is a different operational commitment than one that takes 6 minutes |
| Cache hit rate | `cache_read_input_tokens / (cache_read_input_tokens + input_tokens + cache_creation_input_tokens)`, aggregated across the run | Diagnoses whether prompt caching (below) is actually working, not just declared |

None of this needs the answer key — it's read straight off `response.usage` on every model call the
system already makes, which is also the point: efficiency evals cost nothing extra to collect.

### Lever 1 — prompt caching

The Ledger hands each candidate dossier to two or three specialists, and every one of those ~150–400
calls shares the same static prefix: the specialist's system prompt and the policy-Skill text it
loaded (Module 2). That is exactly the shape prompt caching is for. Mark the shared prefix with a
`cache_control` breakpoint once — render order is `tools → system → messages`, so the breakpoint
goes on the last block of the frozen system-plus-skill text — and the run's later candidates are
billed at roughly a tenth of the first for everything ahead of the per-candidate dossier, which sits
*after* the breakpoint and stays uncached because it's different every time.

**Verify, don't assume.** Learners check `cache_read_input_tokens` on their own run rather than
trusting that adding `cache_control` worked. The classic silent invalidator here is a timestamp, a
per-run UUID, or unsorted JSON baked into what was supposed to be the frozen shared prefix — the
run still completes, still produces correct findings, and silently pays full price on every call
with no error to say so. A prompt that "should" cache and shows `cache_read_input_tokens: 0` across
repeated runs is the signal to go find the invalidator, not a caching failure to route around.

### Lever 2 — batch processing

The Message Batches API cuts cost 50% and fits the shape of a quarterly run precisely: a few hundred
independent, single-shot analyst calls, not latency-sensitive for a compliance workflow that runs
once a quarter, with results back well inside its up-to-24-hour window.

Two things constrain where it applies, and both tie back to decisions the program already made:

- **It doesn't fit the debug loop.** That's exactly what the frozen contract's `limit` parameter is
  for (Module 0) — learners iterate on the fast synchronous path with `limit=20` or so, and reach
  for the Batch API only on the full, `limit=None`, once-a-quarter run. Conflating the two means
  waiting minutes-to-hours for feedback on a prompt tweak, which is the single most likely way this
  program blows its budget (see the parent spec's note on `limit`).
- **It only cleanly covers a single-shot call.** A batch request has no mid-flight tool round-trip —
  it's one request, one response. That's a fit precisely because the Ledger already assembled each
  candidate's dossier before an analyst ever sees it (**"reconciliation is code, judgment is
  agents"** — the architecture's own organizing principle). An analyst design that needs a live MCP
  lookup mid-reasoning for a specific candidate keeps that one call on the synchronous path; the
  rest of the fan-out — the bulk of the volume — batches cleanly.

---

## All the eval types, one table

The taxonomy learners actually need spans effectiveness, efficiency, and the case study's own
graded tiers — and the most important column is the last one, because it draws the line between
what a learner can check themselves and what only the grader ever sees.

| Type | Measures | Scored against | Who runs it | When |
|---|---|---|---|---|
| Schema & coverage validation | Structural correctness | The schema itself | Learner, free | Every run |
| Self-consistency | Prompt stability | Itself (two runs) | Learner, ~2× run cost | Before trusting a prompt change |
| Hand-labeled micro-key | Verdict correctness on a small sample | The learner's own 10–15 labels | Learner, a few hours once | Once, then reused as a regression test |
| Rationale rubric (LLM-as-judge) | Defensibility of reasoning | A judge prompt's rubric | Learner, one call per finding | Every run |
| Cost per review / per finding | Efficiency | The learner's own budget target | Learner, read off `usage` | Every run |
| Wall-clock latency | Efficiency | The learner's own SLA | Learner, timed | Every run |
| Cache hit rate | Efficiency (is caching actually working) | Itself (should trend toward the theoretical ceiling) | Learner, read off `usage` | Every run |
| Must-catch / judgment / traps (case study tiers) | Ground-truth correctness, false-positive rate | The withheld Q3/Q4 answer key | **Grading agent only** | Grading (Module 6 submission) |

The first seven rows are what Module 5 builds and what a learner can run as often as they like with
no key. The last row is why the first seven exist: they're the closest a learner can get to that
score without ever seeing it.

---

## What ships vs. what learners build

Consistent with the kit boundary in Module 0: the kit ships the frozen contract, the schema, and the
`limit` parameter that makes cheap iteration possible. It does not ship an eval harness, a
hand-labeled key, or usage-tracking code — those are the learner's Module 5 deliverable, same as the
Ledger was Module 1's and the specialists were Module 3's.

## Open questions

None outstanding for Module 5.
