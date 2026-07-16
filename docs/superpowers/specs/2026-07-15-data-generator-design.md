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
  apps.yaml                   # 22 apps: roles, privileged flags, owning dept, implementation_date
  sod_matrix.yaml             # conflicting role pairs + documented exemptions
  service_accounts.yaml       # the approved registry (source of trap #1)
  departments.yaml            # org structure and reporting lines
  policies/*.md               # the five prose policy docs
```

Only the people, and what happens to them, vary by seed.

## The world

**Meridian Regional Energy** — a regional gas and electric utility, ~1,200 employees, ~15,000
entitlements across 22 apps. Roughly 12.5 entitlements per person, which is realistic for a company
this size.

### Departments (~1,200 heads)

| Department | Heads | Role in the case study |
|---|---:|---|
| Operations | 380 | The bulk. Plant and dispatch. |
| Field Services | 210 | Heavy contractor mix, mobile access, high turnover |
| Customer Care | 140 | Call center — the churn engine |
| Engineering | 120 | Prod access, deploy rights |
| Information Technology | 60 | Infrastructure, Applications, Security, Service Desk |
| Sales & Key Accounts | 60 | Commercial customers |
| Finance & Accounting | 45 | Where SoD lives |
| Marketing | 25 | |
| Procurement | 20 | The other half of SoD |
| Human Resources | 18 | |
| Legal & Compliance | 12 | |
| Executive | 8 | |

Field Services and Customer Care carry the turnover that makes stale access plausible. Finance and
Procurement are small enough that SoD conflicts are structurally unavoidable — which is the honest
reason real companies carry compensating controls, and what makes the exemption trap fair rather
than a gotcha.

### App catalog — 22 apps, four tiers

| Tier | Apps |
|---|---|
| **Crown jewels** (5) | Atlas ERP, MeridianPay (payroll), Gateway (IdP), Active Directory, Vault (secrets) |
| **Business** (8) | Compass CRM, Helix ITSM, PeopleHub HRIS, Procure, Expense, Tableau, DocuSign, Box |
| **Infrastructure** (5) | GitHub Enterprise, AWS Prod, AWS NonProd, Snowflake, Jenkins |
| **Universal** (4) | Slack, Zoom, VPN, Badge access |

Representative role models on the crown jewels (the apps the SoD matrix and findings depend on):

- **Atlas ERP** — AP Clerk, AP Manager, Vendor Admin, GL Accountant, Controller, ERP Admin
- **MeridianPay** — Payroll Clerk, Payroll Approver, Payroll Admin
- **Gateway** — Help Desk, User Admin, App Admin, Super Admin
- **Active Directory** — Standard, Account Operator, Domain Admin
- **Vault** — Reader, Writer, Admin

The universal apps plus AD and Gateway are held by nearly everyone — roughly half the 15,000
entitlements are boring by construction. That is the volume the Ledger triages away, and the reason
the context-economics lesson survives at 15k just as it would at 40k: candidate count, not row
count, drives cost.

### SoD matrix

| Conflict | Why | Severity |
|---|---|---|
| Atlas: `Vendor Admin` ⊗ `AP Manager` | Create a vendor, then approve its payment | Critical |
| Atlas: `AP Clerk` ⊗ `AP Manager` | Enter an invoice and approve it | High |
| Procure: `Requisitioner` ⊗ `Buyer` ⊗ `Receiver` | Three-way procurement fraud | Critical |
| MeridianPay: `Payroll Clerk` ⊗ `Payroll Approver` | Edit your own pay, approve it | Critical |
| Gateway: `User Admin` ⊗ any app `Admin` | Grant yourself access, then use it | High |
| Helix: `Change Approver` ⊗ AWS Prod `Admin` | Approve your own change, then deploy it | High |

**The documented exemption** (and the SoD trap): Finance is 45 people, and the Controller's
function genuinely requires both `AP Manager` and `Vendor Admin` at a company this size. The Access
Control Policy carries a named exemption with a compensating control — quarterly manual payment
review by the CFO, evidenced in Atlas. So the Controller *looks* like the single worst SoD violation
in the dataset and is entirely correct. Any system that flags it has failed to read the policy it
was given. This is the sharpest test of false-positive discipline in the world.

### Personas

Each persona is a narrative class with a face:

| Persona | Narrative | Class |
|---|---|---|
| The lifer — 19 years, six role changes, sedimented access | `TransferKeptOldAccess` / creep | judgment |
| The transfer — Operations → Finance in March, kept dispatch rights | `TransferKeptOldAccess` | judgment |
| The contractor — SOW expired 3 weeks ago, manager vouched in a ticket | `ContractorOverstayWithVouch` | judgment |
| The boomerang — left 2023, rehired 2025, old account reactivated + new one | duplicate hazard | mess |
| The break-glass — `emergency.admin`, dormant by design, documented | `BreakGlassDormant` | trap |
| The service account with a human name — in the approved registry | `ApprovedServiceAccount` | trap |
| The vendor engineer — third-party, time-boxed prod access | supports must-catch cases | — |
| The intern — 12 weeks, access that should have auto-expired | must-catch source | must_catch |
| The employee on leave — no login in 4 months, not terminated | `EmployeeOnLeave` | trap |

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

The app-scoped coverage-gap cases sit inside these tallies: the two skipped apps count as judgment
cases, the newly-implemented app as a trap. The account/application `scope` field, not the count,
is what keeps them distinct during grading.

### Where findings live

Mostly the crown jewels and infrastructure — Atlas ERP, MeridianPay, Gateway, AD, Vault, AWS Prod,
GitHub — because that is where risk concentrates in real access reviews. Business apps stay clean.

**One deliberate exception:** at least one must-catch case lives in a universal app — a terminated
employee whose Slack is still live. This punishes anyone who hard-codes "only audit the crown
jewels" as a triage shortcut. That assumption is exactly the kind of hidden shortcut the unseen Q4
quarter is meant to expose: it will pass every Q3 test if Q3's terminated-access cases all sit in
Atlas, then fail at grading. Planting one universal-app case in *both* quarters makes the lesson
available in Q3 rather than sprung only at grading — fair warning, not a gotcha.

### Prior-review coverage gaps — an app-scoped challenge

`prior_review.csv` is stubbed (see Output below), and it deliberately does not cover all 22 apps.
**Three apps are absent, for two different reasons — and telling the reasons apart is the
challenge.**

- **Two apps were skipped.** They were in scope, but the Q2 review simply was not performed for
  them. This is a genuine coverage gap.
- **One app is newly implemented this quarter.** It did not exist at Q2, so its absence from the
  prior review is expected, not a gap.

All three look identical in `prior_review.csv`: absent. The discriminator is the app's
`implementation_date` in `apps.yaml`:

- New app → `implementation_date` within the current quarter → absence is **expected**.
- Skipped apps → old implementation date, live entitlements, no prior review → **coverage gap**.

So the correct path is a Ledger reconciliation — *apps with entitlements, minus apps implemented
this quarter, minus apps present in prior review* — feeding a judgment call about what the residual
means.

**Correct behavior:**

- Surface the two skipped apps as a coverage gap (judgment-tier finding).
- Do **not** report the newly-implemented app's missing prior review as a gap (trap).

**Two consequences:**

1. This is a new *kind* of finding. Every other planted case is account-scoped — a person, an
   entitlement. A coverage gap is **app-scoped**. The findings schema therefore carries
   `scope: account | application`, and grading must handle an app-level finding. See the parent
   spec's contract note.
2. **Seed-varied, not fixed.** The generator picks which app is newly implemented and which two are
   skipped per seed. If the skipped pair were constant, a learner could hard-code those app names
   and pass Q4 for the wrong reason. Varying them forces the reconciliation, which is the lesson.
   The stub is programmatic, so this costs nothing.

Making an app "newly implemented this quarter" means the generator stamps its `implementation_date`
inside the quarter being generated and dates all its entitlement grants recently (a fresh rollout —
everyone provisioned at once). Because each quarter is generated self-contained, the same app may be
"new" in Q3 and a different app "new" in Q4; learners never see the two side by side, so there is no
inconsistency to notice.

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
      "scope": "account",
      "subject": { "employee_id": "...", "account_id": "...", "app": "...", "entitlement": "..." },
      "expected": { "category": "terminated_access", "recommendation": "revoke" },
      "rationale_must_reference": ["term_date", "ACP-4.2"]
    },
    {
      "case_id": "...",
      "narrative": "PriorReviewCoverageGap",
      "class": "judgment",
      "scope": "application",
      "subject": { "app": "Box" },
      "expected": { "category": "coverage_gap", "recommendation": "review" },
      "rationale_must_reference": ["not_in_prior_review", "implementation_date"]
    }
  ]
}
```

Traps appear as cases with `class: "trap"` and an empty `expected` — their presence in the key means
*no finding should exist for this subject*. The newly-implemented app is such a trap:
`scope: "application"`, empty `expected`, meaning no coverage-gap finding should be raised for it.

`scope` distinguishes account-level cases (the subject is a person's entitlement) from
application-level cases (the subject is an app). Grading reads it to know whether to look for a
per-account finding or an app-level one.

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

1. ~~Name/identity source — Faker vs. a committed `names.txt`.~~ **Resolved: Faker**, seeded
   deterministically from the run's RNG. It only ever touches the *surface* of a person (name,
   email, title) and never the answer key, and it makes the `Bob Smith` → `robert.smith` mismatch
   hazard trivial. The version is pinned in `pyproject.toml` so determinism cannot drift across
   Faker releases.
2. ~~Is `prior_review.csv` generated or stubbed?~~ **Resolved: stubbed.** Rather than simulate a
   full Q2, the generator writes a plausible prior review against the current quarter's accounts.
   It deliberately omits three apps to create the coverage-gap challenge above (two skipped, one
   newly implemented). Stubbing also makes narrative-specific prior-review rows — e.g. "this
   contractor was conditionally approved last quarter" — trivial to author alongside the narrative
   that needs them.
