# Meridian Data Generator — Design

**Status:** draft for review · 15 July 2026
**Parent:** [Meridian UAR Capstone Program](./2026-07-15-uar-capstone-design.md)
**Position:** first sub-project. Everything downstream — the `run_review()` contract, the module
curricula, the grading agent — keys off the answer key this produces.

---

## Purpose

Produce a quarter of synthetic user-access-review data for a fictional company, together with an
answer key that is correct by construction, from a single integer seed.

Two consumers:

1. **Learners** receive `--seed A` (Q3) *with* its answer key, and build against it.
2. **The grading agent** runs their `run_review()` against `--seed B` (Q4), a quarter they have
   never seen, and scores it against that quarter's key.

The entire grading model rests on one property: **the answer key must never lie.** If a case in the
key is not genuinely derivable from the emitted artifacts, a correct system is marked wrong. That
property gets a test, not a comment.

---

## Shape: a fixed world, a random cast

The generator does not generate everything. Meridian's app catalog, role definitions, SoD matrix,
and policy corpus are **static, hand-authored assets**, identical across every seed.

Two reasons. Real companies do not rewrite policy every quarter. More practically, the SoD matrix
must reference real app roles by name — if both sides are random, the policies become meaningless
noise and the traps become unauthorable.

```
world/                        # static, version-controlled, seed-independent
  apps.yaml                   # 40 apps: roles, privileged flags, owning dept
  sod_matrix.yaml             # conflicting role pairs + documented exemptions
  service_accounts.yaml       # the approved registry (source of trap #1)
  departments.yaml            # org structure and reporting lines
  policies/*.md               # the five prose policy docs
```

Only the people, and what happens to them, vary by seed.

---

## Narratives: the core abstraction

Each employee is assigned a storyline. The generator emits HR rows, entitlements, and tickets
*consistent with that storyline*. The answer key falls out of the narrative assignment.

```python
class Narrative:
    weight: float           # relative frequency
    finding_class: str      # must_catch | judgment | trap | clean

    def emit(person, world, rng) -> (hr_rows, iam_rows, ticket_rows): ...
    def expected_findings(person) -> list[Finding]: ...
```

One narrative, one file, one purpose — independently testable, and readable without reading the
generator's internals.

This is what makes labels incapable of drifting from data: **the data is derived from the label.**
`TerminatedWithActiveAdmin` does not annotate a finding. It writes a term date into the HR roster,
*and* leaves the admin entitlement live, *and* omits the revocation ticket. The key is a byproduct
of having done those three things.

### The cast

Roughly 96% of ~1,200 employees draw a clean narrative. The rest draw from twelve planted
storylines, mapping one-to-one onto the taxonomy in the parent spec.

| Narrative | Class |
|---|---|
| `CleanFTE` | clean |
| `CleanContractor` | clean |
| `CleanTransfer` | clean |
| `CleanPrivileged` | clean |
| `TerminatedWithActiveAdmin` | must_catch |
| `OrphanNoHRRecord` | must_catch |
| `PrivilegedGrantNoTicket` | must_catch |
| `GrantBeforeHireDate` | must_catch |
| `DormantPrivileged` | must_catch |
| `ContractorOverstayWithVouch` | judgment |
| `TransferKeptOldAccess` | judgment |
| `SoDConflictWithCompensatingControl` | judgment |
| `ApprovedServiceAccount` | trap |
| `BreakGlassDormant` | trap |
| `EmployeeOnLeave` | trap |
| `ExemptedSoDPair` | trap |

### Case volume

**~45 planted cases per quarter: 24 must-catch, 9 judgment, 12 traps.**

Enough that catch rate and false-positive rate are statistically meaningful; small enough that a
human reviewer could plausibly work the queue. Roughly mirrors real UAR finding density (~3–4% of
the population).

---

## The anti-leak obligation

If planted cases are detectable by any shortcut, the grading model collapses — a learner who notices
"every orphan has an account ID above 9000" scores perfectly with a `grep`, and a hard-coded system
becomes indistinguishable from a working one.

Explicit obligations, enforced by test:

- Account and employee IDs never encode narrative or class
- Row order in every export is shuffled
- Planted cases are distributed across departments and apps, never clustered
- Clean and planted accounts share the same distributions for incidental fields (a planted orphan's
  `granted_date` must look like any other `granted_date`)

---

## Deliberate messes

Mostly clean, with roughly half a dozen documented hazards. Enough to make the Ledger a real join
without risking a Module 1 pile-up.

| Hazard | Forces |
|---|---|
| Name-format mismatch HR vs IAM (`Bob Smith` / `robert.smith`), ~10% of accounts | Join on email or employee ID, not name |
| Two date formats in the IAM export | Normalization before comparison |
| Null `last_login` on never-logged-in accounts | Distinguishing "never" from "not recently" |
| A few duplicate account rows | Deduplication before counting |
| Casing and whitespace drift in department names | Canonicalization |

Documented in the repo for the instructor. **Discovered** by learners — the kit says the data is
messy, as real exports are, without enumerating how.

---

## Output

```
data/2026-Q3/
  hr_roster.csv
  entitlements.csv
  access_tickets.json
  prior_review.csv
  policies/              # copied from world/, so export_dir is self-contained
answer_key.json          # written beside, never inside
```

CSV for the tabular exports because that is what IAM and HR teams actually hand you, and parsing
them is the Module 1 lesson rather than an obstacle to it. JSON for tickets, which are genuinely
nested.

The key lives **outside** the export directory so that shipping the directory can never leak it.

`run_review(export_dir)` sees exactly this shape.

### Answer key format

```json
{
  "seed": 20260715,
  "quarter": "2026-Q4",
  "counts": { "must_catch": 24, "judgment": 9, "trap": 12, "clean": 1155 },
  "cases": [
    {
      "case_id": "...",
      "narrative": "TerminatedWithActiveAdmin",
      "class": "must_catch",
      "subject": { "employee_id": "...", "account_id": "...", "app": "...", "entitlement": "..." },
      "expected": { "category": "terminated_access", "recommendation": "revoke" },
      "rationale_must_reference": ["term_date", "ACP-4.2"]
    }
  ]
}
```

Traps appear as cases with `class: "trap"` and an empty `expected` — their presence in the key means
*no finding should exist for this subject*.

---

## Q3 and Q4

**Same generator, different seed.** Q3 is `--seed A`; Q4 is `--seed B`. No difficulty bump, no
novel narrative held back.

This guarantees fairness — the graded quarter cannot be harder than what they trained against — and
means Module 6's self-test (regenerate with your own seed, run against it) is genuinely the same
procedure as grading, rather than a rehearsal of it. Any generator bug hits both quarters equally.

---

## Determinism

- One `random.Random(seed)` threaded through explicitly. No global `random`, no module-level state.
- No `datetime.now()`. Quarter-end is a parameter.
- Stable ID assignment independent of iteration order.

Same seed must produce byte-identical output. This is the first test.

---

## Interface

```
python -m meridian.generate --seed 20260715 --quarter 2026-Q3 --out data/2026-Q3/
python -m meridian.generate --seed 20260715 --quarter 2026-Q3 --out data/2026-Q3/ --key answer_key.json
```

---

## Tests

**Coherence** — the important one. For every case in the answer key, assert the finding is actually
derivable from the emitted artifacts. If `TerminatedWithActiveAdmin` claims a finding, the HR row
must genuinely carry a term date before quarter-end and the entitlement must genuinely still be
live. This is the generator's own eval: it proves the key doesn't lie, which is the single property
the grading model rests on.

**Determinism** — same seed twice, byte-identical output.

**Anti-leak** — planted case IDs are distributed indistinguishably from clean ones; no clustering by
department, app, or ID range.

**Counts** — each class hits its target within tolerance.

---

## Open questions

1. Employee name source — a names library, or a hand-curated list? A library adds a dependency;
   a curated list risks visible repetition at 1,200 rows.
2. Should `prior_review.csv` (last quarter's decisions) itself be generated from a prior seed, or
   hand-stubbed? Generating it properly implies simulating Q2, which may be more machinery than the
   case study needs.
