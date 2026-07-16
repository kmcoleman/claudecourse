# Meridian Data Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic generator that emits one quarter of synthetic user-access-review data (HR roster, entitlements, tickets, prior review, policies) plus a correct-by-construction answer key, from a single integer seed.

**Architecture:** A fixed, hand-authored world (apps, departments, SoD matrix, policies) loaded from YAML, populated by a random cast. Each employee is assigned a *narrative* (a storyline) whose `emit()` produces artifacts consistent with that story and whose `expected_findings()` produces the answer-key cases — so labels are derived from data and cannot drift. A CLI orchestrates: load world → build population → assign narratives → emit artifacts → inject deliberate messes → shuffle → write files + key.

**Tech Stack:** Python 3.11+, `faker` (seedable identities), `pyyaml` (world assets), `pytest`.

## Global Constraints

- **Python 3.11+** — uses `X | None` union syntax and `datetime.date`.
- **Determinism is absolute.** One `random.Random(seed)` (and one `Faker` seeded from it) threaded explicitly. No global `random`, no module-level mutable state, no `datetime.now()` / `date.today()`. The quarter-end date is always a parameter. Same seed → byte-identical output.
- **Dependencies:** `faker`, `pyyaml`, `pytest` only. Nothing else.
- **The answer key must never lie.** Every case in the key must be genuinely derivable from the emitted artifacts. This is enforced by the coherence test (Task 18), which is the single most important test in the project.
- **World is seed-independent.** Files under `world/` never vary by seed. Only the cast and what happens to them vary.
- **Anti-leak:** account/employee IDs never encode narrative or class; all exported rows are shuffled; planted cases spread across departments/apps; incidental fields share distributions between clean and planted rows.
- **Company facts (verbatim):** Meridian Regional Energy, ~1,200 employees, 22 apps, ~15,000 entitlements. Planted target: **24 must_catch, 9 judgment, 13 trap** per quarter (46 total). The 13 traps = 12 account-scoped trap narratives + 1 application-scoped new-app trap. The 9 judgment = 7 account-scoped + 2 application-scoped coverage-gap cases.
- **Package layout:** all importable code under `meridian/`; tests under `tests/`; world assets under `world/`.

---

## File Structure

```
pyproject.toml                  # package + deps
world/
  apps.yaml                     # 22 apps: tier, roles, privileged_roles, owning_dept, implementation_date
  departments.yaml              # 12 departments + headcounts
  sod_matrix.yaml               # conflicts + the Controller exemption
  service_accounts.yaml         # approved service-account registry
  policies/
    access-control-policy.md    # names the Controller exemption (clause ACP-4.2)
    privileged-access-standard.md
    contractor-access-standard.md
    termination-procedure.md
    sod-policy.md
meridian/
  __init__.py
  rng.py                        # deterministic RNG + Faker factory
  models.py                     # dataclasses: Person, Entitlement, Ticket, PriorReviewRow, Case, EmitResult, World, AppSelection
  world.py                      # load_world() -> World
  identity.py                   # seedable names/emails + name-mismatch hazard
  population.py                 # build_population() -> list[Person]
  entitlements.py               # baseline_entitlements(person, world, rng)
  narratives/
    __init__.py                 # NARRATIVES registry
    base.py                     # Narrative base class
    clean.py                    # CleanFTE, CleanContractor, CleanTransfer, CleanPrivileged
    must_catch.py               # 5 must-catch narratives
    judgment.py                 # ContractorOverstayWithVouch, TransferKeptOldAccess, SoDConflictWithCompensatingControl
    traps.py                    # ApprovedServiceAccount, BreakGlassDormant, EmployeeOnLeave, ExemptedSoDPair
  app_selection.py              # choose new + 2 skipped apps; build coverage-gap cases
  prior_review.py               # stubbed prior review honoring the app omissions
  cast.py                       # assign narratives to the population at target counts
  messes.py                     # inject the documented deliberate messes
  emit.py                       # write CSV / JSON / copy policies
  answer_key.py                 # assemble + write answer_key.json
  generate.py                   # __main__ CLI orchestration
tests/
  test_rng.py  test_models.py  test_world.py  test_identity.py
  test_population.py  test_entitlements.py  test_narratives_clean.py
  test_narratives_must_catch.py  test_narratives_judgment.py
  test_narratives_traps.py  test_app_selection.py  test_prior_review.py
  test_cast.py  test_messes.py  test_emit.py  test_answer_key.py
  test_coherence.py  test_acceptance.py
```

---

### Task 1: Project scaffold + deterministic RNG

**Files:**
- Create: `pyproject.toml`, `meridian/__init__.py`, `meridian/rng.py`
- Test: `tests/test_rng.py`

**Interfaces:**
- Produces: `meridian.rng.make_rng(seed: int) -> random.Random`; `meridian.rng.make_faker(rng: random.Random) -> faker.Faker` (a `Faker` instance seeded deterministically from `rng`).

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "meridian"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["faker>=25", "pyyaml>=6"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["meridian*"]
```

- [ ] **Step 2: Create `meridian/__init__.py`** (empty file).

- [ ] **Step 3: Write the failing test** in `tests/test_rng.py`

```python
from meridian.rng import make_rng, make_faker


def test_make_rng_is_deterministic():
    a = make_rng(42)
    b = make_rng(42)
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]


def test_make_faker_is_deterministic():
    fa = make_faker(make_rng(42))
    fb = make_faker(make_rng(42))
    assert [fa.name() for _ in range(5)] == [fb.name() for _ in range(5)]


def test_different_seeds_differ():
    assert make_rng(1).random() != make_rng(2).random()
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pip install -e ".[dev]" && pytest tests/test_rng.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` for `meridian.rng`.

- [ ] **Step 5: Write `meridian/rng.py`**

```python
import random

from faker import Faker


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


def make_faker(rng: random.Random) -> Faker:
    fake = Faker("en_US")
    fake.seed_instance(rng.randint(0, 2**32 - 1))
    return fake
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_rng.py -v`
Expected: PASS (3 passed).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml meridian/__init__.py meridian/rng.py tests/test_rng.py
git commit -m "feat: project scaffold and deterministic RNG"
```

---

### Task 2: Data models

**Files:**
- Create: `meridian/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces the frozen/dataclasses used everywhere downstream:
  - `Person(employee_id: str, full_name: str, email: str, department: str, title: str, hire_date: date, term_date: date | None, employment_type: str, status: str, in_hr: bool)` — frozen.
  - `Entitlement(account_id: str, account_name: str, app: str, role: str, granted_date: date, granted_by: str, last_login: date | None)`.
  - `Ticket(ticket_id: str, account_id: str, app: str, role: str, requested_date: date, approver: str, status: str)`.
  - `PriorReviewRow(account_id: str, app: str, reviewer: str, decision: str, review_date: date)`.
  - `Case(case_id: str, narrative: str, finding_class: str, scope: str, subject: dict, expected: dict, rationale_must_reference: list[str])`.
  - `EmitResult(hr_rows: list[Person], iam_rows: list[Entitlement], tickets: list[Ticket], prior_review_rows: list[PriorReviewRow], cases: list[Case])`.
  - `App(name: str, tier: str, roles: list[str], privileged_roles: list[str], owning_dept: str, implementation_date: date)`.
  - `World(apps: dict[str, App], departments: dict[str, int], sod_conflicts: list[dict], sod_exemptions: list[dict], service_accounts: list[str], policies_dir: str)`.
  - `AppSelection(new_app: str, skipped_apps: list[str])`.
  - Constants: `employment_type` ∈ {`"FTE"`, `"Contractor"`}; `status` ∈ {`"active"`, `"terminated"`, `"on_leave"`}; `finding_class` ∈ {`"must_catch"`, `"judgment"`, `"trap"`, `"clean"`}; `scope` ∈ {`"account"`, `"application"`}.

- [ ] **Step 1: Write the failing test** in `tests/test_models.py`

```python
from datetime import date

from meridian.models import Person, Entitlement, Case, EmitResult


def test_person_is_frozen_and_replaceable():
    from dataclasses import replace
    p = Person("E1", "Bob Smith", "bob@x.com", "Finance", "Clerk",
               date(2020, 1, 1), None, "FTE", "active", True)
    p2 = replace(p, status="terminated", term_date=date(2026, 3, 1))
    assert p.status == "active" and p2.status == "terminated"


def test_emit_result_defaults_empty():
    r = EmitResult(hr_rows=[], iam_rows=[], tickets=[], prior_review_rows=[], cases=[])
    assert r.cases == []


def test_case_holds_scope_and_expected():
    c = Case("c1", "TerminatedWithActiveAdmin", "must_catch", "account",
             {"account_id": "A1"}, {"recommendation": "revoke"}, ["term_date"])
    assert c.scope == "account" and c.expected["recommendation"] == "revoke"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ImportError` for `meridian.models`.

- [ ] **Step 3: Write `meridian/models.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Person:
    employee_id: str
    full_name: str
    email: str
    department: str
    title: str
    hire_date: date
    term_date: date | None
    employment_type: str   # "FTE" | "Contractor"
    status: str            # "active" | "terminated" | "on_leave"
    in_hr: bool            # False => orphan account, no HR record


@dataclass
class Entitlement:
    account_id: str
    account_name: str
    app: str
    role: str
    granted_date: date
    granted_by: str
    last_login: date | None


@dataclass
class Ticket:
    ticket_id: str
    account_id: str
    app: str
    role: str
    requested_date: date
    approver: str
    status: str            # "approved" | "pending" | "denied"


@dataclass
class PriorReviewRow:
    account_id: str
    app: str
    reviewer: str
    decision: str          # "approved" | "revoked" | "conditional"
    review_date: date


@dataclass
class Case:
    case_id: str
    narrative: str
    finding_class: str     # "must_catch" | "judgment" | "trap"
    scope: str             # "account" | "application"
    subject: dict
    expected: dict         # {} for traps
    rationale_must_reference: list[str]


@dataclass
class EmitResult:
    hr_rows: list[Person] = field(default_factory=list)
    iam_rows: list[Entitlement] = field(default_factory=list)
    tickets: list[Ticket] = field(default_factory=list)
    prior_review_rows: list[PriorReviewRow] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)


@dataclass(frozen=True)
class App:
    name: str
    tier: str              # "crown" | "business" | "infra" | "universal"
    roles: list[str]
    privileged_roles: list[str]
    owning_dept: str
    implementation_date: date


@dataclass(frozen=True)
class World:
    apps: dict              # name -> App
    departments: dict       # name -> headcount:int
    sod_conflicts: list     # list[dict]
    sod_exemptions: list    # list[dict]
    service_accounts: list  # list[str]
    policies_dir: str


@dataclass(frozen=True)
class AppSelection:
    new_app: str
    skipped_apps: list[str]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/models.py tests/test_models.py
git commit -m "feat: core data models"
```

---

### Task 3: World assets + loader

**Files:**
- Create: `world/apps.yaml`, `world/departments.yaml`, `world/sod_matrix.yaml`, `world/service_accounts.yaml`, `world/policies/*.md`, `meridian/world.py`
- Test: `tests/test_world.py`

**Interfaces:**
- Consumes: `meridian.models.App`, `World`.
- Produces: `meridian.world.load_world(root: str = "world") -> World`.

- [ ] **Step 1: Write `world/departments.yaml`**

```yaml
# name: headcount  (sums to 1200)
Operations: 380
Field Services: 210
Customer Care: 140
Engineering: 120
Information Technology: 60
Sales & Key Accounts: 60
Finance & Accounting: 45
Marketing: 25
Procurement: 20
Human Resources: 18
Legal & Compliance: 12
Executive: 8
```

- [ ] **Step 2: Write `world/apps.yaml`** (22 apps; `implementation_date` is a legacy date for all — the generator overrides the chosen "new" app per seed)

```yaml
# tier: crown | business | infra | universal
# implementation_date: default legacy date; the per-seed new app is overridden at generation time.
Atlas ERP:        {tier: crown,      owning_dept: Finance & Accounting, implementation_date: 2014-05-01, roles: [AP Clerk, AP Manager, Vendor Admin, GL Accountant, Controller, ERP Admin], privileged_roles: [Vendor Admin, Controller, ERP Admin]}
MeridianPay:      {tier: crown,      owning_dept: Human Resources,      implementation_date: 2016-02-01, roles: [Payroll Clerk, Payroll Approver, Payroll Admin], privileged_roles: [Payroll Approver, Payroll Admin]}
Gateway:          {tier: crown,      owning_dept: Information Technology, implementation_date: 2013-09-01, roles: [Help Desk, User Admin, App Admin, Super Admin], privileged_roles: [User Admin, App Admin, Super Admin]}
Active Directory: {tier: crown,      owning_dept: Information Technology, implementation_date: 2010-01-01, roles: [Standard, Account Operator, Domain Admin], privileged_roles: [Account Operator, Domain Admin]}
Vault:            {tier: crown,      owning_dept: Information Technology, implementation_date: 2018-06-01, roles: [Reader, Writer, Admin], privileged_roles: [Admin]}
Compass CRM:      {tier: business,   owning_dept: Sales & Key Accounts,  implementation_date: 2017-03-01, roles: [User, Manager, Admin], privileged_roles: [Admin]}
Helix ITSM:       {tier: business,   owning_dept: Information Technology, implementation_date: 2015-07-01, roles: [Agent, Change Approver, Admin], privileged_roles: [Change Approver, Admin]}
PeopleHub HRIS:   {tier: business,   owning_dept: Human Resources,       implementation_date: 2016-08-01, roles: [Employee, HR Partner, Admin], privileged_roles: [Admin]}
Procure:          {tier: business,   owning_dept: Procurement,           implementation_date: 2017-11-01, roles: [Requisitioner, Buyer, Receiver, Admin], privileged_roles: [Admin]}
Expense:          {tier: business,   owning_dept: Finance & Accounting,  implementation_date: 2018-01-01, roles: [Submitter, Approver, Admin], privileged_roles: [Admin]}
Tableau:          {tier: business,   owning_dept: Engineering,           implementation_date: 2019-04-01, roles: [Viewer, Author, Admin], privileged_roles: [Admin]}
DocuSign:         {tier: business,   owning_dept: Legal & Compliance,    implementation_date: 2018-09-01, roles: [Sender, Admin], privileged_roles: [Admin]}
Box:              {tier: business,   owning_dept: Information Technology, implementation_date: 2016-05-01, roles: [Member, Co-Owner, Admin], privileged_roles: [Admin]}
GitHub Enterprise: {tier: infra,     owning_dept: Engineering,           implementation_date: 2017-02-01, roles: [Member, Maintainer, Org Admin], privileged_roles: [Org Admin]}
AWS Prod:         {tier: infra,      owning_dept: Engineering,           implementation_date: 2016-06-01, roles: [ReadOnly, Developer, Admin], privileged_roles: [Admin]}
AWS NonProd:      {tier: infra,      owning_dept: Engineering,           implementation_date: 2016-06-01, roles: [ReadOnly, Developer, Admin], privileged_roles: [Admin]}
Snowflake:        {tier: infra,      owning_dept: Engineering,           implementation_date: 2020-10-01, roles: [Reader, Analyst, SysAdmin], privileged_roles: [SysAdmin]}
Jenkins:          {tier: infra,      owning_dept: Engineering,           implementation_date: 2015-01-01, roles: [Viewer, Builder, Admin], privileged_roles: [Admin]}
Slack:            {tier: universal,  owning_dept: Information Technology, implementation_date: 2016-01-01, roles: [Member, Admin], privileged_roles: [Admin]}
Zoom:             {tier: universal,  owning_dept: Information Technology, implementation_date: 2017-01-01, roles: [Member, Admin], privileged_roles: [Admin]}
VPN:              {tier: universal,  owning_dept: Information Technology, implementation_date: 2012-01-01, roles: [User], privileged_roles: []}
Badge access:     {tier: universal,  owning_dept: Operations,            implementation_date: 2009-01-01, roles: [Standard, Facilities Admin], privileged_roles: [Facilities Admin]}
```

- [ ] **Step 3: Write `world/sod_matrix.yaml`**

```yaml
conflicts:
  - {app: Atlas ERP, roles: [Vendor Admin, AP Manager], severity: critical, why: "Create a vendor, then approve its payment"}
  - {app: Atlas ERP, roles: [AP Clerk, AP Manager], severity: high, why: "Enter an invoice and approve it"}
  - {app: Procure, roles: [Requisitioner, Buyer, Receiver], severity: critical, why: "Three-way procurement fraud"}
  - {app: MeridianPay, roles: [Payroll Clerk, Payroll Approver], severity: critical, why: "Edit your own pay, approve it"}
  - {app: Gateway, roles: [User Admin], cross_app_admin: true, severity: high, why: "Grant yourself access, then use it"}
  - {app: Helix ITSM, roles: [Change Approver], cross_app: {app: AWS Prod, role: Admin}, severity: high, why: "Approve your own change, then deploy it"}
exemptions:
  - {app: Atlas ERP, roles: [Vendor Admin, AP Manager], department: Finance & Accounting, title: Controller, clause: ACP-4.2, compensating_control: "Quarterly manual payment review by the CFO, evidenced in Atlas"}
```

- [ ] **Step 4: Write `world/service_accounts.yaml`**

```yaml
# Approved service accounts in the registry. Human-looking names are deliberate (trap source).
- svc-atlas-batch
- svc-backup-runner
- marcus.pipeline        # human-looking service account (ApprovedServiceAccount trap)
- svc-gateway-sync
- emergency.admin        # break-glass, dormant by design (BreakGlassDormant trap)
```

- [ ] **Step 5: Write the five policy files** under `world/policies/`. The Access Control Policy MUST name the Controller exemption at clause ACP-4.2 (the SoD trap's correctness depends on it).

`world/policies/access-control-policy.md`:

```markdown
# Meridian Regional Energy — Access Control Policy (ACP)

## ACP-1 Purpose
Access to Meridian systems is granted on least-privilege and reviewed quarterly.

## ACP-4 Segregation of Duties
ACP-4.1 Conflicting duties defined in the SoD matrix must not be held by one individual.

ACP-4.2 **Documented exemption.** Where business necessity requires conflicting roles, an
exemption may be granted in writing by the CFO with a compensating control. The standing
exemption: the **Controller** in Finance & Accounting may hold both `AP Manager` and
`Vendor Admin` in Atlas ERP. Compensating control: quarterly manual payment review by the CFO,
evidenced in Atlas. Access held under ACP-4.2 is **not** a finding.

## ACP-6 Termination
Access is revoked on the employee's termination date (see Termination Procedure).
```

`world/policies/privileged-access-standard.md`:

```markdown
# Privileged Access Standard
Privileged roles require an approved access request (ticket) before grant, and must show
activity within 180 days or be reviewed for removal. Break-glass accounts are exempt from the
dormancy rule when registered and documented.
```

`world/policies/contractor-access-standard.md`:

```markdown
# Contractor Access Standard
Contractor access ends on the statement-of-work end date. Extensions require a new approved
ticket referencing the renewed SOW before the prior end date.
```

`world/policies/termination-procedure.md`:

```markdown
# Termination Procedure
On an employee's termination date, all access is revoked within 24 hours. Employees on approved
leave retain access; leave is not termination.
```

`world/policies/sod-policy.md`:

```markdown
# Segregation of Duties Policy
See the SoD matrix for conflicting role pairs. Conflicts are findings unless covered by a
documented exemption under ACP-4.2.
```

- [ ] **Step 6: Write the failing test** in `tests/test_world.py`

```python
from datetime import date
from meridian.world import load_world


def test_world_loads_all_apps_and_departments():
    w = load_world("world")
    assert len(w.apps) == 22
    assert sum(w.departments.values()) == 1200
    assert "Atlas ERP" in w.apps


def test_app_fields_parsed():
    w = load_world("world")
    atlas = w.apps["Atlas ERP"]
    assert atlas.tier == "crown"
    assert "Vendor Admin" in atlas.privileged_roles
    assert isinstance(atlas.implementation_date, date)


def test_sod_exemption_present():
    w = load_world("world")
    assert any(e["clause"] == "ACP-4.2" for e in w.sod_exemptions)
```

- [ ] **Step 7: Run test to verify it fails**

Run: `pytest tests/test_world.py -v`
Expected: FAIL with `ImportError` for `meridian.world`.

- [ ] **Step 8: Write `meridian/world.py`**

```python
from __future__ import annotations

import os

import yaml

from meridian.models import App, World


def load_world(root: str = "world") -> World:
    with open(os.path.join(root, "apps.yaml")) as f:
        apps_raw = yaml.safe_load(f)
    apps = {}
    for name, d in apps_raw.items():
        apps[name] = App(
            name=name,
            tier=d["tier"],
            roles=list(d["roles"]),
            privileged_roles=list(d.get("privileged_roles", [])),
            owning_dept=d["owning_dept"],
            implementation_date=d["implementation_date"],
        )
    with open(os.path.join(root, "departments.yaml")) as f:
        departments = yaml.safe_load(f)
    with open(os.path.join(root, "sod_matrix.yaml")) as f:
        sod = yaml.safe_load(f)
    with open(os.path.join(root, "service_accounts.yaml")) as f:
        service_accounts = yaml.safe_load(f)
    return World(
        apps=apps,
        departments=departments,
        sod_conflicts=sod["conflicts"],
        sod_exemptions=sod["exemptions"],
        service_accounts=service_accounts,
        policies_dir=os.path.join(root, "policies"),
    )
```

Note: PyYAML parses unquoted `2014-05-01` as a `datetime.date`, so `implementation_date` is already a `date`.

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/test_world.py -v`
Expected: PASS (3 passed).

- [ ] **Step 10: Commit**

```bash
git add world/ meridian/world.py tests/test_world.py
git commit -m "feat: world assets and loader"
```

---

### Task 4: Identity generation

**Files:**
- Create: `meridian/identity.py`
- Test: `tests/test_identity.py`

**Interfaces:**
- Consumes: `meridian.rng.make_faker`.
- Produces:
  - `make_identity(faker, rng, mismatch: bool = False) -> tuple[str, str, str]` returning `(full_name, account_name, email)`. When `mismatch=False`, `account_name` is derived directly from `full_name` (e.g. `bob.smith`); when `mismatch=True`, `account_name` uses a different form (e.g. `bsmith` or a nickname) so a name-based join fails while the email still resolves.
  - `email_for(full_name: str) -> str` deterministic helper.

- [ ] **Step 1: Write the failing test** in `tests/test_identity.py`

```python
from meridian.identity import make_identity, email_for
from meridian.rng import make_rng, make_faker


def test_email_is_deterministic_from_name():
    assert email_for("Bob Smith") == "bob.smith@meridian-energy.com"


def test_no_mismatch_account_matches_name():
    rng = make_rng(1)
    fake = make_faker(rng)
    full, account, email = make_identity(fake, rng, mismatch=False)
    # account_name is a normalized form of the full name
    assert account.replace(".", " ").split()[0].lower() in full.lower()


def test_mismatch_breaks_name_join():
    rng = make_rng(1)
    fake = make_faker(rng)
    full, account, email = make_identity(fake, rng, mismatch=True)
    # the account_name is NOT the plain firstname.lastname form
    assert account != full.lower().replace(" ", ".")
    # but the email still resolves to the person
    assert email == email_for(full)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_identity.py -v`
Expected: FAIL with `ImportError` for `meridian.identity`.

- [ ] **Step 3: Write `meridian/identity.py`**

```python
from __future__ import annotations

import re

DOMAIN = "meridian-energy.com"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z]+", ".", name.lower()).strip(".")


def email_for(full_name: str) -> str:
    return f"{_slug(full_name)}@{DOMAIN}"


def make_identity(faker, rng, mismatch: bool = False) -> tuple[str, str, str]:
    full = faker.name()
    # strip any Faker prefixes/suffixes to keep names two-part and clean
    parts = [p for p in full.split() if p.isalpha()]
    if len(parts) < 2:
        parts = [faker.first_name(), faker.last_name()]
    first, last = parts[0], parts[-1]
    full = f"{first} {last}"
    email = email_for(full)
    if mismatch:
        style = rng.choice(["initial_last", "first_initial", "nickname"])
        if style == "initial_last":
            account = f"{first[0].lower()}{last.lower()}"
        elif style == "first_initial":
            account = f"{first.lower()}{last[0].lower()}"
        else:
            account = f"{faker.first_name().lower()}.{last.lower()}"
    else:
        account = f"{first.lower()}.{last.lower()}"
    return full, account, email
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_identity.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/identity.py tests/test_identity.py
git commit -m "feat: seedable identity generation with name-mismatch hazard"
```

---

### Task 5: Population builder

**Files:**
- Create: `meridian/population.py`
- Test: `tests/test_population.py`

**Interfaces:**
- Consumes: `World`, `make_faker`, `make_identity`, `email_for`.
- Produces: `build_population(world: World, rng, faker, quarter_end: date) -> list[Person]` — one `Person` per headcount (1,200 total), all `status="active"`, `term_date=None`, `in_hr=True`, `employment_type` mostly `"FTE"` with a realistic contractor fraction in Field Services. Hire dates are before `quarter_end`. Employee IDs are `E00001`…`E01200` assigned after a shuffle so ID order does not encode department.

- [ ] **Step 1: Write the failing test** in `tests/test_population.py`

```python
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population


def test_population_size_matches_headcount():
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    assert len(pop) == 1200


def test_ids_unique_and_zero_padded():
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    ids = [p.employee_id for p in pop]
    assert len(set(ids)) == 1200
    assert all(i.startswith("E") and len(i) == 6 for i in ids)


def test_hire_dates_before_quarter_end():
    w = load_world("world")
    rng = make_rng(7)
    qe = date(2026, 9, 30)
    pop = build_population(w, rng, make_faker(rng), qe)
    assert all(p.hire_date < qe for p in pop)


def test_contractors_exist_and_are_minority():
    w = load_world("world")
    rng = make_rng(7)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    contractors = [p for p in pop if p.employment_type == "Contractor"]
    assert 0 < len(contractors) < 300
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_population.py -v`
Expected: FAIL with `ImportError` for `meridian.population`.

- [ ] **Step 3: Write `meridian/population.py`**

```python
from __future__ import annotations

from datetime import date, timedelta

from meridian.identity import make_identity
from meridian.models import Person, World

# departments with a meaningful contractor share
_CONTRACTOR_RATE = {"Field Services": 0.35, "Customer Care": 0.15, "Engineering": 0.10}


def _hire_date(rng, quarter_end: date) -> date:
    # uniformly within ~15 years before quarter end
    days = rng.randint(60, 365 * 15)
    return quarter_end - timedelta(days=days)


def build_population(world: World, rng, faker, quarter_end: date) -> list[Person]:
    people: list[Person] = []
    for dept, headcount in world.departments.items():
        rate = _CONTRACTOR_RATE.get(dept, 0.0)
        for _ in range(headcount):
            is_contractor = rng.random() < rate
            mismatch = rng.random() < 0.10          # ~10% name-format mismatch hazard
            full, _account, email = make_identity(faker, rng, mismatch=mismatch)
            people.append(Person(
                employee_id="PENDING",
                full_name=full,
                email=email,
                department=dept,
                title=faker.job()[:40],
                hire_date=_hire_date(rng, quarter_end),
                term_date=None,
                employment_type="Contractor" if is_contractor else "FTE",
                status="active",
                in_hr=True,
            ))
    rng.shuffle(people)                              # ID order must not encode department
    from dataclasses import replace
    return [replace(p, employee_id=f"E{i + 1:05d}") for i, p in enumerate(people)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_population.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/population.py tests/test_population.py
git commit -m "feat: population builder"
```

---

### Task 6: Baseline entitlements

**Files:**
- Create: `meridian/entitlements.py`
- Test: `tests/test_entitlements.py`

**Interfaces:**
- Consumes: `World`, `Person`, `Entitlement`, `make_identity`.
- Produces:
  - `account_name_for(person, rng, faker) -> str` — the IAM display name; may mismatch the HR name (~10%).
  - `baseline_entitlements(person, world, rng, faker, quarter_end, account_id) -> list[Entitlement]` — the boring volume. Everyone gets the universal apps + AD Standard + Gateway Help Desk-or-Standard; some get department-appropriate business/infra roles. Averages ~12 rows/person so the full population lands near 15,000. `last_login` is within ~90 days for active users, sometimes `None`. All `granted_date` values are before `quarter_end`.

- [ ] **Step 1: Write the failing test** in `tests/test_entitlements.py`

```python
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.entitlements import baseline_entitlements


def test_everyone_has_universal_apps():
    w = load_world("world")
    rng = make_rng(3)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    p = build_population(w, rng, fake, qe)[0]
    ents = baseline_entitlements(p, w, rng, fake, qe, account_id="A000001")
    apps = {e.app for e in ents}
    assert {"Slack", "VPN", "Active Directory"} <= apps


def test_grant_dates_before_quarter_end():
    w = load_world("world")
    rng = make_rng(3)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    p = build_population(w, rng, fake, qe)[0]
    ents = baseline_entitlements(p, w, rng, fake, qe, account_id="A000001")
    assert all(e.granted_date < qe for e in ents)


def test_population_entitlement_total_in_range():
    w = load_world("world")
    rng = make_rng(3)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    pop = build_population(w, rng, fake, qe)
    total = sum(len(baseline_entitlements(p, w, rng, fake, qe, f"A{i:06d}"))
               for i, p in enumerate(pop))
    assert 12000 <= total <= 18000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_entitlements.py -v`
Expected: FAIL with `ImportError` for `meridian.entitlements`.

- [ ] **Step 3: Write `meridian/entitlements.py`**

```python
from __future__ import annotations

from datetime import date, timedelta

from meridian.identity import make_identity
from meridian.models import Entitlement, Person, World

_UNIVERSAL = ["Slack", "Zoom", "VPN", "Badge access"]
_ALWAYS = ["Active Directory", "Gateway"]
# department -> extra business/infra apps its members commonly hold
_DEPT_APPS = {
    "Engineering": ["GitHub Enterprise", "AWS NonProd", "AWS Prod", "Jenkins", "Tableau"],
    "Finance & Accounting": ["Atlas ERP", "Expense", "Tableau"],
    "Procurement": ["Procure", "Atlas ERP"],
    "Human Resources": ["PeopleHub HRIS", "MeridianPay"],
    "Sales & Key Accounts": ["Compass CRM", "DocuSign"],
    "Information Technology": ["Helix ITSM", "Box", "Vault", "Snowflake"],
    "Legal & Compliance": ["DocuSign", "Box"],
    "Customer Care": ["Compass CRM", "Helix ITSM"],
    "Operations": ["Helix ITSM"],
}


def account_name_for(person: Person, rng, faker) -> str:
    # reuse identity logic: derive an IAM-side account name from the person's name
    _full, account, _email = make_identity(faker, rng, mismatch=False)
    # keep it tied to the real person: base it on their stored name
    first = person.full_name.split()[0].lower()
    last = person.full_name.split()[-1].lower()
    return f"{first}.{last}"


def _grant(app: str, role: str, person: Person, rng, qe: date, account_id: str,
           account_name: str) -> Entitlement:
    granted = qe - timedelta(days=rng.randint(30, 365 * 6))
    last_login = None if rng.random() < 0.08 else qe - timedelta(days=rng.randint(0, 90))
    return Entitlement(
        account_id=account_id,
        account_name=account_name,
        app=app,
        role=role,
        granted_date=granted,
        granted_by=rng.choice(["gateway.provisioning", "helpdesk", "manager.approval"]),
        last_login=last_login,
    )


def baseline_entitlements(person: Person, world: World, rng, faker, quarter_end: date,
                          account_id: str) -> list[Entitlement]:
    account_name = account_name_for(person, rng, faker)
    ents: list[Entitlement] = []
    for app in _UNIVERSAL:
        role = world.apps[app].roles[0]
        ents.append(_grant(app, role, person, rng, quarter_end, account_id, account_name))
    ents.append(_grant("Active Directory", "Standard", person, rng, quarter_end,
                       account_id, account_name))
    ents.append(_grant("Gateway", "Help Desk" if person.department ==
                       "Information Technology" else "Help Desk", person, rng,
                       quarter_end, account_id, account_name))
    for app in _DEPT_APPS.get(person.department, []):
        if rng.random() < 0.6:
            role = rng.choice(world.apps[app].roles[:2])   # low-privilege by default
            ents.append(_grant(app, role, person, rng, quarter_end, account_id, account_name))
    return ents
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_entitlements.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/entitlements.py tests/test_entitlements.py
git commit -m "feat: baseline entitlement assignment"
```

---

### Task 7: Narrative base class + registry

**Files:**
- Create: `meridian/narratives/__init__.py`, `meridian/narratives/base.py`
- Test: (covered by Task 8's tests; this task adds no standalone test beyond an import check)

**Interfaces:**
- Consumes: `EmitResult`, `Person`, `World`, `baseline_entitlements`.
- Produces:
  - `class Narrative` with class attributes `name: str`, `finding_class: str`, `weight: float`, and method `emit(self, person: Person, world: World, rng, faker, quarter_end: date, account_id: str) -> EmitResult`. The base `emit` returns baseline entitlements + the person as an HR row and no cases; subclasses override.
  - `meridian.narratives.NARRATIVES: dict[str, Narrative]` — the registry, populated in Task 13's imports. Task 7 creates it empty with a `register()` helper.
  - `next_account_id(counter: int) -> str` helper → `f"A{counter:06d}"`.

- [ ] **Step 1: Write `meridian/narratives/base.py`**

```python
from __future__ import annotations

from meridian.entitlements import baseline_entitlements
from meridian.models import EmitResult, Person, World


class Narrative:
    name: str = "Narrative"
    finding_class: str = "clean"
    weight: float = 0.0

    def emit(self, person: Person, world: World, rng, faker, quarter_end,
             account_id: str) -> EmitResult:
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        return EmitResult(hr_rows=[person], iam_rows=ents)
```

- [ ] **Step 2: Write `meridian/narratives/__init__.py`**

```python
from __future__ import annotations

from meridian.narratives.base import Narrative

NARRATIVES: dict[str, Narrative] = {}


def register(narrative: Narrative) -> Narrative:
    NARRATIVES[narrative.name] = narrative
    return narrative


def next_account_id(counter: int) -> str:
    return f"A{counter:06d}"
```

- [ ] **Step 3: Verify import**

Run: `python -c "from meridian.narratives import NARRATIVES, register, next_account_id; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add meridian/narratives/__init__.py meridian/narratives/base.py
git commit -m "feat: narrative base class and registry"
```

---

### Task 8: Clean narratives

**Files:**
- Create: `meridian/narratives/clean.py`
- Test: `tests/test_narratives_clean.py`

**Interfaces:**
- Consumes: `Narrative`, `register`, `baseline_entitlements`.
- Produces registered instances `CleanFTE`, `CleanContractor`, `CleanTransfer`, `CleanPrivileged`, each `finding_class="clean"`, each `emit()` returning artifacts with **zero cases**. `CleanPrivileged` adds one privileged role *with* a matching approval ticket and recent login (so it is legitimately clean). `CleanTransfer` shows a department change but with old access already removed.

- [ ] **Step 1: Write the failing test** in `tests/test_narratives_clean.py`

```python
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.clean import CleanFTE, CleanPrivileged


def _ctx():
    w = load_world("world")
    rng = make_rng(5)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_clean_fte_has_no_cases():
    w, rng, fake, qe, person = _ctx()
    r = CleanFTE.emit(person, w, rng, fake, qe, "A000001")
    assert r.cases == []
    assert r.hr_rows == [person]


def test_clean_privileged_has_ticket_and_no_cases():
    w, rng, fake, qe, person = _ctx()
    r = CleanPrivileged.emit(person, w, rng, fake, qe, "A000002")
    assert r.cases == []
    priv = [e for e in r.iam_rows if e.role in
            {ro for a in w.apps.values() for ro in a.privileged_roles}]
    assert priv, "expected at least one privileged entitlement"
    assert r.tickets, "privileged grant must have an approval ticket"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_narratives_clean.py -v`
Expected: FAIL with `ImportError` for `meridian.narratives.clean`.

- [ ] **Step 3: Write `meridian/narratives/clean.py`**

```python
from __future__ import annotations

from datetime import timedelta

from meridian.entitlements import baseline_entitlements
from meridian.models import EmitResult, Entitlement, Ticket
from meridian.narratives import register
from meridian.narratives.base import Narrative


class _CleanFTE(Narrative):
    name = "CleanFTE"
    finding_class = "clean"
    weight = 70.0


class _CleanContractor(Narrative):
    name = "CleanContractor"
    finding_class = "clean"
    weight = 12.0


class _CleanTransfer(Narrative):
    name = "CleanTransfer"
    finding_class = "clean"
    weight = 8.0


class _CleanPrivileged(Narrative):
    name = "CleanPrivileged"
    finding_class = "clean"
    weight = 6.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        app = "Vault"
        role = "Admin"
        granted = quarter_end - timedelta(days=rng.randint(60, 400))
        ents.append(Entitlement(account_id, ents[0].account_name, app, role, granted,
                                "gateway.provisioning",
                                quarter_end - timedelta(days=rng.randint(0, 20))))
        ticket = Ticket(f"REQ-{account_id}", account_id, app, role,
                        granted - timedelta(days=2), "manager.approval", "approved")
        return EmitResult(hr_rows=[person], iam_rows=ents, tickets=[ticket])


CleanFTE = register(_CleanFTE())
CleanContractor = register(_CleanContractor())
CleanTransfer = register(_CleanTransfer())
CleanPrivileged = register(_CleanPrivileged())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_narratives_clean.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/narratives/clean.py tests/test_narratives_clean.py
git commit -m "feat: clean narratives"
```

---

### Task 9: Must-catch narratives

**Files:**
- Create: `meridian/narratives/must_catch.py`
- Test: `tests/test_narratives_must_catch.py`

**Interfaces:**
- Consumes: `Narrative`, `register`, `baseline_entitlements`, `Case`, `Entitlement`, `Ticket`.
- Produces registered instances, each `finding_class="must_catch"`, each emitting exactly one account-scoped `Case`:
  - `TerminatedWithActiveAdmin` — sets `term_date` before `quarter_end`, `status="terminated"`, leaves a live privileged entitlement, no revocation. One case targets a crown-jewel or (for the deliberate exception) a universal app; a flag `universal: bool` on the instance forces Slack.
  - `OrphanNoHRRecord` — `in_hr=False` (person omitted from HR roster), entitlements exist. Case subject has null `employee_id`.
  - `PrivilegedGrantNoTicket` — privileged entitlement with no matching ticket.
  - `GrantBeforeHireDate` — an entitlement whose `granted_date` precedes `hire_date`.
  - `DormantPrivileged` — privileged entitlement, `last_login` > 180 days before `quarter_end`.

- [ ] **Step 1: Write the failing test** in `tests/test_narratives_must_catch.py`

```python
from datetime import date, timedelta
from dataclasses import replace
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.must_catch import (
    TerminatedWithActiveAdmin, OrphanNoHRRecord, DormantPrivileged, GrantBeforeHireDate,
)


def _ctx(seed=9):
    w = load_world("world")
    rng = make_rng(seed)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_terminated_sets_term_date_and_keeps_admin():
    w, rng, fake, qe, person = _ctx()
    r = TerminatedWithActiveAdmin.emit(person, w, rng, fake, qe, "A000010")
    assert len(r.cases) == 1
    assert r.hr_rows[0].term_date is not None and r.hr_rows[0].term_date < qe
    assert r.hr_rows[0].status == "terminated"
    privileged = {ro for a in w.apps.values() for ro in a.privileged_roles}
    assert any(e.role in privileged for e in r.iam_rows)


def test_orphan_has_no_hr_row():
    w, rng, fake, qe, person = _ctx()
    r = OrphanNoHRRecord.emit(person, w, rng, fake, qe, "A000011")
    assert r.hr_rows == []
    assert r.iam_rows
    assert r.cases[0].subject.get("employee_id") in (None, "")


def test_dormant_last_login_exceeds_180_days():
    w, rng, fake, qe, person = _ctx()
    r = DormantPrivileged.emit(person, w, rng, fake, qe, "A000012")
    flagged = r.cases[0].subject["account_id"]
    ent = [e for e in r.iam_rows if e.account_id == flagged and e.last_login][0]
    assert (qe - ent.last_login).days > 180


def test_grant_before_hire_is_actually_before():
    w, rng, fake, qe, person = _ctx()
    r = GrantBeforeHireDate.emit(person, w, rng, fake, qe, "A000013")
    hire = r.hr_rows[0].hire_date
    bad = [e for e in r.iam_rows if e.granted_date < hire]
    assert bad, "expected an entitlement granted before hire date"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_narratives_must_catch.py -v`
Expected: FAIL with `ImportError` for `meridian.narratives.must_catch`.

- [ ] **Step 3: Write `meridian/narratives/must_catch.py`**

```python
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from meridian.entitlements import baseline_entitlements
from meridian.models import Case, EmitResult, Entitlement
from meridian.narratives import register
from meridian.narratives.base import Narrative


def _priv_grant(account_id, account_name, app, role, granted_date, last_login):
    return Entitlement(account_id, account_name, app, role, granted_date,
                       "gateway.provisioning", last_login)


class _TerminatedWithActiveAdmin(Narrative):
    name = "TerminatedWithActiveAdmin"
    finding_class = "must_catch"
    weight = 0.0
    universal = False   # set True on the Slack instance

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        term = quarter_end - timedelta(days=rng.randint(15, 120))
        person = replace(person, status="terminated", term_date=term)
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        if self.universal:
            app, role = "Slack", "Admin"
        else:
            app, role = "Active Directory", "Domain Admin"
        ents.append(_priv_grant(account_id, name, app, role,
                                quarter_end - timedelta(days=400),
                                term - timedelta(days=5)))
        case = Case(f"case-{account_id}", self.name, "must_catch", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": app, "entitlement": role},
                    {"category": "terminated_access", "recommendation": "revoke"},
                    ["term_date"])
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


class _OrphanNoHRRecord(Narrative):
    name = "OrphanNoHRRecord"
    finding_class = "must_catch"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        person = replace(person, in_hr=False)
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        case = Case(f"case-{account_id}", self.name, "must_catch", "account",
                    {"employee_id": None, "account_id": account_id,
                     "app": ents[-1].app, "entitlement": ents[-1].role},
                    {"category": "orphan_account", "recommendation": "revoke"},
                    ["no_hr_record"])
        return EmitResult(hr_rows=[], iam_rows=ents, cases=[case])


class _PrivilegedGrantNoTicket(Narrative):
    name = "PrivilegedGrantNoTicket"
    finding_class = "must_catch"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        app, role = "AWS Prod", "Admin"
        ents.append(_priv_grant(account_id, name, app, role,
                                quarter_end - timedelta(days=rng.randint(30, 300)),
                                quarter_end - timedelta(days=rng.randint(0, 60))))
        case = Case(f"case-{account_id}", self.name, "must_catch", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": app, "entitlement": role},
                    {"category": "no_approval", "recommendation": "review"},
                    ["no_ticket"])
        # deliberately emit NO ticket
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


class _GrantBeforeHireDate(Narrative):
    name = "GrantBeforeHireDate"
    finding_class = "must_catch"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        app, role = "GitHub Enterprise", "Org Admin"
        ents.append(_priv_grant(account_id, name, app, role,
                                person.hire_date - timedelta(days=rng.randint(5, 60)),
                                quarter_end - timedelta(days=rng.randint(0, 60))))
        case = Case(f"case-{account_id}", self.name, "must_catch", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": app, "entitlement": role},
                    {"category": "grant_before_hire", "recommendation": "review"},
                    ["hire_date", "granted_date"])
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


class _DormantPrivileged(Narrative):
    name = "DormantPrivileged"
    finding_class = "must_catch"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        app, role = "Vault", "Admin"
        ents.append(_priv_grant(account_id, name, app, role,
                                quarter_end - timedelta(days=500),
                                quarter_end - timedelta(days=rng.randint(200, 400))))
        case = Case(f"case-{account_id}", self.name, "must_catch", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": app, "entitlement": role},
                    {"category": "dormant_privileged", "recommendation": "revoke"},
                    ["last_login"])
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


TerminatedWithActiveAdmin = register(_TerminatedWithActiveAdmin())
OrphanNoHRRecord = register(_OrphanNoHRRecord())
PrivilegedGrantNoTicket = register(_PrivilegedGrantNoTicket())
GrantBeforeHireDate = register(_GrantBeforeHireDate())
DormantPrivileged = register(_DormantPrivileged())

# a second terminated instance forced onto a universal app (the deliberate exception)
_terminated_slack = _TerminatedWithActiveAdmin()
_terminated_slack.name = "TerminatedWithActiveAdminUniversal"
_terminated_slack.universal = True
TerminatedWithActiveAdminUniversal = register(_terminated_slack)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_narratives_must_catch.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/narratives/must_catch.py tests/test_narratives_must_catch.py
git commit -m "feat: must-catch narratives"
```

---

### Task 10: Judgment narratives

**Files:**
- Create: `meridian/narratives/judgment.py`
- Test: `tests/test_narratives_judgment.py`

**Interfaces:**
- Consumes: `Narrative`, `register`, `baseline_entitlements`, `Case`, `Entitlement`, `Ticket`, `PriorReviewRow`.
- Produces, each `finding_class="judgment"`, each emitting one account-scoped `Case` with `expected["recommendation"] == "review"` (no single right verdict):
  - `ContractorOverstayWithVouch` — contractor whose `term_date` (SOW end) is ~3 weeks before `quarter_end`, `status` still `active`, plus a ticket where the manager vouches, plus a `PriorReviewRow` with `decision="conditional"`.
  - `TransferKeptOldAccess` — a transfer that retains a prior-department entitlement (privilege creep).
  - `SoDConflictWithCompensatingControl` — holds a conflicting Atlas pair but is **not** the Controller (so it is a real conflict), with a compensating-control note referenced in the rationale.

- [ ] **Step 1: Write the failing test** in `tests/test_narratives_judgment.py`

```python
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.judgment import (
    ContractorOverstayWithVouch, TransferKeptOldAccess, SoDConflictWithCompensatingControl,
)


def _ctx(seed=11):
    w = load_world("world")
    rng = make_rng(seed)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_contractor_overstay_has_vouch_ticket_and_conditional_prior():
    w, rng, fake, qe, person = _ctx()
    r = ContractorOverstayWithVouch.emit(person, w, rng, fake, qe, "A000020")
    assert r.cases[0].finding_class == "judgment"
    assert r.cases[0].expected["recommendation"] == "review"
    assert r.tickets, "expected a vouch ticket"
    assert any(pr.decision == "conditional" for pr in r.prior_review_rows)


def test_sod_conflict_holds_both_roles():
    w, rng, fake, qe, person = _ctx()
    r = SoDConflictWithCompensatingControl.emit(person, w, rng, fake, qe, "A000021")
    roles = {e.role for e in r.iam_rows if e.app == "Atlas ERP"}
    assert {"Vendor Admin", "AP Manager"} <= roles
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_narratives_judgment.py -v`
Expected: FAIL with `ImportError` for `meridian.narratives.judgment`.

- [ ] **Step 3: Write `meridian/narratives/judgment.py`**

```python
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from meridian.entitlements import baseline_entitlements
from meridian.models import Case, EmitResult, Entitlement, PriorReviewRow, Ticket
from meridian.narratives import register
from meridian.narratives.base import Narrative


class _ContractorOverstayWithVouch(Narrative):
    name = "ContractorOverstayWithVouch"
    finding_class = "judgment"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        sow_end = quarter_end - timedelta(days=rng.randint(14, 28))
        person = replace(person, employment_type="Contractor", term_date=sow_end,
                         status="active")
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        ticket = Ticket(f"REQ-{account_id}", account_id, "VPN", "User",
                        sow_end - timedelta(days=3),
                        "manager.approval", "approved")  # the manager vouched
        prior = PriorReviewRow(account_id, "VPN", "prior.reviewer", "conditional",
                               quarter_end - timedelta(days=90))
        case = Case(f"case-{account_id}", self.name, "judgment", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": "VPN", "entitlement": "User"},
                    {"category": "contractor_overstay", "recommendation": "review"},
                    ["term_date", "vouch_ticket"])
        return EmitResult(hr_rows=[person], iam_rows=ents, tickets=[ticket],
                          prior_review_rows=[prior], cases=[case])


class _TransferKeptOldAccess(Narrative):
    name = "TransferKeptOldAccess"
    finding_class = "judgment"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        person = replace(person, department="Finance & Accounting")
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        # retained old-department access: a dispatch/ops entitlement
        old = Entitlement(account_id, name, "Helix ITSM", "Change Approver",
                          quarter_end - timedelta(days=700), "gateway.provisioning",
                          quarter_end - timedelta(days=rng.randint(0, 45)))
        ents.append(old)
        case = Case(f"case-{account_id}", self.name, "judgment", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": "Helix ITSM", "entitlement": "Change Approver"},
                    {"category": "privilege_creep", "recommendation": "review"},
                    ["department_change", "granted_date"])
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


class _SoDConflictWithCompensatingControl(Narrative):
    name = "SoDConflictWithCompensatingControl"
    finding_class = "judgment"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        person = replace(person, department="Finance & Accounting", title="Senior Accountant")
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        for role in ("Vendor Admin", "AP Manager"):
            ents.append(Entitlement(account_id, name, "Atlas ERP", role,
                                    quarter_end - timedelta(days=rng.randint(60, 500)),
                                    "gateway.provisioning",
                                    quarter_end - timedelta(days=rng.randint(0, 30))))
        case = Case(f"case-{account_id}", self.name, "judgment", "account",
                    {"employee_id": person.employee_id, "account_id": account_id,
                     "app": "Atlas ERP", "entitlement": "Vendor Admin+AP Manager"},
                    {"category": "sod_conflict", "recommendation": "review"},
                    ["sod_matrix", "compensating_control"])
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


ContractorOverstayWithVouch = register(_ContractorOverstayWithVouch())
TransferKeptOldAccess = register(_TransferKeptOldAccess())
SoDConflictWithCompensatingControl = register(_SoDConflictWithCompensatingControl())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_narratives_judgment.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/narratives/judgment.py tests/test_narratives_judgment.py
git commit -m "feat: judgment narratives"
```

---

### Task 11: Trap narratives

**Files:**
- Create: `meridian/narratives/traps.py`
- Test: `tests/test_narratives_traps.py`

**Interfaces:**
- Consumes: `Narrative`, `register`, `baseline_entitlements`, `Case`, `Entitlement`, `PriorReviewRow`, `World.service_accounts`.
- Produces, each `finding_class="trap"`, each emitting one `Case` with **empty `expected` `{}`** (meaning: no finding should be raised):
  - `ApprovedServiceAccount` — an account whose name is in the approved registry (`marcus.pipeline`), privileged, dormant — but legitimate. HR row omitted (service accounts aren't people).
  - `BreakGlassDormant` — `emergency.admin`, dormant by design, in the registry.
  - `EmployeeOnLeave` — `status="on_leave"`, no login in ~120 days, not terminated (`term_date=None`).
  - `ExemptedSoDPair` — the Controller holding `Vendor Admin` + `AP Manager` under exemption ACP-4.2.

- [ ] **Step 1: Write the failing test** in `tests/test_narratives_traps.py`

```python
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.narratives.traps import (
    ApprovedServiceAccount, BreakGlassDormant, EmployeeOnLeave, ExemptedSoDPair,
)


def _ctx(seed=13):
    w = load_world("world")
    rng = make_rng(seed)
    fake = make_faker(rng)
    qe = date(2026, 9, 30)
    person = build_population(w, rng, fake, qe)[0]
    return w, rng, fake, qe, person


def test_traps_have_empty_expected():
    w, rng, fake, qe, person = _ctx()
    for i, narr in enumerate([ApprovedServiceAccount, BreakGlassDormant,
                              EmployeeOnLeave, ExemptedSoDPair]):
        r = narr.emit(person, w, rng, fake, qe, f"A0000{i}0")
        assert r.cases[0].finding_class == "trap"
        assert r.cases[0].expected == {}


def test_on_leave_not_terminated():
    w, rng, fake, qe, person = _ctx()
    r = EmployeeOnLeave.emit(person, w, rng, fake, qe, "A000030")
    assert r.hr_rows[0].status == "on_leave"
    assert r.hr_rows[0].term_date is None


def test_service_account_name_in_registry():
    w, rng, fake, qe, person = _ctx()
    r = ApprovedServiceAccount.emit(person, w, rng, fake, qe, "A000031")
    assert any(e.account_name in w.service_accounts for e in r.iam_rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_narratives_traps.py -v`
Expected: FAIL with `ImportError` for `meridian.narratives.traps`.

- [ ] **Step 3: Write `meridian/narratives/traps.py`**

```python
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from meridian.entitlements import baseline_entitlements
from meridian.models import Case, EmitResult, Entitlement
from meridian.narratives import register
from meridian.narratives.base import Narrative


def _trap_case(account_id, narrative, subject):
    return Case(f"case-{account_id}", narrative, "trap", subject.pop("_scope", "account"),
                subject, {}, [])


class _ApprovedServiceAccount(Narrative):
    name = "ApprovedServiceAccount"
    finding_class = "trap"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        acct = "marcus.pipeline"   # human-looking, in the registry
        ents = [Entitlement(account_id, acct, "Atlas ERP", "ERP Admin",
                            quarter_end - timedelta(days=800), "gateway.provisioning",
                            quarter_end - timedelta(days=rng.randint(1, 5)))]
        case = _trap_case(account_id, self.name,
                          {"employee_id": None, "account_id": account_id,
                           "app": "Atlas ERP", "entitlement": "ERP Admin"})
        return EmitResult(hr_rows=[], iam_rows=ents, cases=[case])


class _BreakGlassDormant(Narrative):
    name = "BreakGlassDormant"
    finding_class = "trap"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        acct = "emergency.admin"
        ents = [Entitlement(account_id, acct, "Active Directory", "Domain Admin",
                            quarter_end - timedelta(days=1000), "security.team",
                            quarter_end - timedelta(days=rng.randint(220, 400)))]
        case = _trap_case(account_id, self.name,
                          {"employee_id": None, "account_id": account_id,
                           "app": "Active Directory", "entitlement": "Domain Admin"})
        return EmitResult(hr_rows=[], iam_rows=ents, cases=[case])


class _EmployeeOnLeave(Narrative):
    name = "EmployeeOnLeave"
    finding_class = "trap"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        person = replace(person, status="on_leave", term_date=None)
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        for i, e in enumerate(ents):
            ents[i] = replace(e, last_login=quarter_end - timedelta(days=rng.randint(110, 140)))
        case = _trap_case(account_id, self.name,
                          {"employee_id": person.employee_id, "account_id": account_id,
                           "app": ents[0].app, "entitlement": ents[0].role})
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


class _ExemptedSoDPair(Narrative):
    name = "ExemptedSoDPair"
    finding_class = "trap"
    weight = 0.0

    def emit(self, person, world, rng, faker, quarter_end, account_id):
        person = replace(person, department="Finance & Accounting", title="Controller")
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        name = ents[0].account_name
        for role in ("Vendor Admin", "AP Manager"):
            ents.append(Entitlement(account_id, name, "Atlas ERP", role,
                                    quarter_end - timedelta(days=rng.randint(200, 900)),
                                    "gateway.provisioning",
                                    quarter_end - timedelta(days=rng.randint(0, 20))))
        case = _trap_case(account_id, self.name,
                          {"employee_id": person.employee_id, "account_id": account_id,
                           "app": "Atlas ERP", "entitlement": "Vendor Admin+AP Manager"})
        return EmitResult(hr_rows=[person], iam_rows=ents, cases=[case])


ApprovedServiceAccount = register(_ApprovedServiceAccount())
BreakGlassDormant = register(_BreakGlassDormant())
EmployeeOnLeave = register(_EmployeeOnLeave())
ExemptedSoDPair = register(_ExemptedSoDPair())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_narratives_traps.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/narratives/traps.py tests/test_narratives_traps.py
git commit -m "feat: trap narratives"
```

---

### Task 12: App selection + coverage-gap cases

**Files:**
- Create: `meridian/app_selection.py`
- Test: `tests/test_app_selection.py`

**Interfaces:**
- Consumes: `World`, `AppSelection`, `Case`.
- Produces:
  - `choose_apps(world, rng) -> AppSelection` — picks 1 `new_app` (from business/infra tier only — never crown or universal) and 2 `skipped_apps` (distinct, from business tier only), seed-varied.
  - `effective_impl_date(app_name, selection, world, quarter_start) -> date` — returns a date *inside the quarter* for the new app, otherwise the world default.
  - `coverage_gap_cases(selection) -> list[Case]` — two judgment app-scoped cases (one per skipped app) with `expected={"category": "coverage_gap", "recommendation": "review"}`, plus one trap app-scoped case for the new app with `expected={}`.

- [ ] **Step 1: Write the failing test** in `tests/test_app_selection.py`

```python
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng
from meridian.app_selection import choose_apps, coverage_gap_cases, effective_impl_date


def test_selection_disjoint_and_correct_tiers():
    w = load_world("world")
    sel = choose_apps(w, make_rng(4))
    assert sel.new_app not in sel.skipped_apps
    assert len(set(sel.skipped_apps)) == 2
    assert w.apps[sel.new_app].tier in {"business", "infra"}
    for a in sel.skipped_apps:
        assert w.apps[a].tier == "business"


def test_new_app_impl_date_inside_quarter():
    w = load_world("world")
    sel = choose_apps(w, make_rng(4))
    qs = date(2026, 7, 1)
    d = effective_impl_date(sel.new_app, sel, w, qs)
    assert d >= qs


def test_coverage_gap_cases_shape():
    w = load_world("world")
    sel = choose_apps(w, make_rng(4))
    cases = coverage_gap_cases(sel)
    gaps = [c for c in cases if c.expected]
    traps = [c for c in cases if not c.expected]
    assert len(gaps) == 2 and len(traps) == 1
    assert all(c.scope == "application" for c in cases)


def test_selection_is_seed_varied():
    w = load_world("world")
    s1 = choose_apps(w, make_rng(1))
    s2 = choose_apps(w, make_rng(99))
    assert (s1.new_app, s1.skipped_apps) != (s2.new_app, s2.skipped_apps)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_selection.py -v`
Expected: FAIL with `ImportError` for `meridian.app_selection`.

- [ ] **Step 3: Write `meridian/app_selection.py`**

```python
from __future__ import annotations

from datetime import date, timedelta

from meridian.models import AppSelection, Case, World


def choose_apps(world: World, rng) -> AppSelection:
    new_candidates = sorted(n for n, a in world.apps.items()
                            if a.tier in {"business", "infra"})
    new_app = rng.choice(new_candidates)
    skip_candidates = sorted(n for n, a in world.apps.items()
                             if a.tier == "business" and n != new_app)
    skipped = rng.sample(skip_candidates, 2)
    return AppSelection(new_app=new_app, skipped_apps=sorted(skipped))


def effective_impl_date(app_name: str, selection: AppSelection, world: World,
                        quarter_start: date) -> date:
    if app_name == selection.new_app:
        return quarter_start + timedelta(days=20)
    return world.apps[app_name].implementation_date


def coverage_gap_cases(selection: AppSelection) -> list[Case]:
    cases = []
    for app in selection.skipped_apps:
        cases.append(Case(f"case-gap-{app}", "PriorReviewCoverageGap", "judgment",
                          "application", {"app": app},
                          {"category": "coverage_gap", "recommendation": "review"},
                          ["not_in_prior_review", "implementation_date"]))
    cases.append(Case(f"case-newapp-{selection.new_app}", "NewAppNoPriorReview", "trap",
                      "application", {"app": selection.new_app}, {}, []))
    return cases
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app_selection.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/app_selection.py tests/test_app_selection.py
git commit -m "feat: app selection and coverage-gap cases"
```

---

### Task 13: Prior-review stub

**Files:**
- Create: `meridian/prior_review.py`
- Test: `tests/test_prior_review.py`

**Interfaces:**
- Consumes: `Entitlement`, `PriorReviewRow`, `AppSelection`.
- Produces: `build_prior_review(iam_rows: list[Entitlement], selection: AppSelection, narrative_rows: list[PriorReviewRow], rng, quarter_end) -> list[PriorReviewRow]` — for every app **except** the new app and the two skipped apps, emit an approved prior-review row for a sampled subset of that app's accounts, then append the narrative-specific rows (e.g. the contractor's conditional). The new + skipped apps produce **no** rows.

- [ ] **Step 1: Write the failing test** in `tests/test_prior_review.py`

```python
from datetime import date, timedelta
from meridian.models import Entitlement, AppSelection
from meridian.rng import make_rng
from meridian.prior_review import build_prior_review


def _ent(app, aid):
    return Entitlement(aid, "x.y", app, "User", date(2025, 1, 1), "gw", date(2026, 9, 1))


def test_skipped_and_new_apps_absent():
    rows = [_ent("Box", "A1"), _ent("Expense", "A2"), _ent("Slack", "A3"),
            _ent("Snowflake", "A4")]
    sel = AppSelection(new_app="Snowflake", skipped_apps=["Box", "Expense"])
    pr = build_prior_review(rows, sel, [], make_rng(1), date(2026, 9, 30))
    covered = {r.app for r in pr}
    assert "Snowflake" not in covered
    assert "Box" not in covered and "Expense" not in covered
    assert "Slack" in covered


def test_narrative_rows_appended():
    from meridian.models import PriorReviewRow
    rows = [_ent("Slack", "A3")]
    sel = AppSelection(new_app="Snowflake", skipped_apps=["Box", "Expense"])
    nar = [PriorReviewRow("A9", "VPN", "prior.reviewer", "conditional", date(2026, 6, 1))]
    pr = build_prior_review(rows, sel, nar, make_rng(1), date(2026, 9, 30))
    assert any(r.decision == "conditional" for r in pr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prior_review.py -v`
Expected: FAIL with `ImportError` for `meridian.prior_review`.

- [ ] **Step 3: Write `meridian/prior_review.py`**

```python
from __future__ import annotations

from datetime import timedelta

from meridian.models import AppSelection, Entitlement, PriorReviewRow


def build_prior_review(iam_rows: list[Entitlement], selection: AppSelection,
                       narrative_rows: list[PriorReviewRow], rng, quarter_end) -> list[PriorReviewRow]:
    omit = {selection.new_app, *selection.skipped_apps}
    rows: list[PriorReviewRow] = []
    for e in iam_rows:
        if e.app in omit:
            continue
        if rng.random() < 0.5:                 # a plausible subset was reviewed
            rows.append(PriorReviewRow(
                account_id=e.account_id,
                app=e.app,
                reviewer="prior.reviewer",
                decision="approved",
                review_date=quarter_end - timedelta(days=rng.randint(80, 100)),
            ))
    rows.extend(narrative_rows)
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prior_review.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/prior_review.py tests/test_prior_review.py
git commit -m "feat: stubbed prior review honoring app omissions"
```

---

### Task 14: Cast assignment

**Files:**
- Create: `meridian/cast.py`
- Test: `tests/test_cast.py`

**Interfaces:**
- Consumes: `NARRATIVES`, all narrative modules (imported for their side-effect registration), `Person`.
- Produces:
  - `PLANTED_PLAN: dict[str, int]` — how many of each **account-scoped** planted narrative to assign. It sums to **43**: 24 must_catch + 7 account-scoped judgment + 12 account-scoped trap. The application-scoped coverage cases (2 judgment skipped-apps + 1 trap new-app) are added separately in Task 12/18, bringing the quarter totals to 24 must_catch, 9 judgment, 13 trap (46 planted).
  - `assign_narratives(population, rng) -> list[tuple[Person, str]]` — returns each person paired with a narrative name. Exactly `PLANTED_PLAN` people (chosen at random, spread across departments) get planted narratives; the rest get a clean narrative sampled by weight.

- [ ] **Step 1: Write the failing test** in `tests/test_cast.py`

```python
from datetime import date
from collections import Counter
from meridian.world import load_world
from meridian.rng import make_rng, make_faker
from meridian.population import build_population
from meridian.cast import assign_narratives, PLANTED_PLAN
from meridian.narratives import NARRATIVES


def test_planted_counts_hit_targets():
    w = load_world("world")
    rng = make_rng(21)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    pairs = assign_narratives(pop, rng)
    counts = Counter(name for _, name in pairs)
    by_class = Counter()
    for name, n in counts.items():
        by_class[NARRATIVES[name].finding_class] += n
    assert by_class["must_catch"] == 24
    assert by_class["trap"] == 12
    # account-scoped judgment (coverage-gap judgments added elsewhere)
    assert by_class["judgment"] == 7


def test_everyone_assigned_once():
    w = load_world("world")
    rng = make_rng(21)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    pairs = assign_narratives(pop, rng)
    assert len(pairs) == len(pop)
    assert {p.employee_id for p, _ in pairs} == {p.employee_id for p in pop}


def test_planted_spread_across_departments():
    w = load_world("world")
    rng = make_rng(21)
    pop = build_population(w, rng, make_faker(rng), date(2026, 9, 30))
    pairs = assign_narratives(pop, rng)
    planted_depts = {p.department for p, name in pairs
                     if NARRATIVES[name].finding_class != "clean"}
    assert len(planted_depts) >= 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cast.py -v`
Expected: FAIL with `ImportError` for `meridian.cast`.

- [ ] **Step 3: Write `meridian/cast.py`**

```python
from __future__ import annotations

# import narrative modules for their registration side effects
import meridian.narratives.clean  # noqa: F401
import meridian.narratives.must_catch  # noqa: F401
import meridian.narratives.judgment  # noqa: F401
import meridian.narratives.traps  # noqa: F401
from meridian.models import Person
from meridian.narratives import NARRATIVES

# Account-scoped planted plan. Coverage-gap judgment cases (2) are added by app_selection,
# bringing judgment to 9 overall; here we plant 7 account-scoped judgment cases.
PLANTED_PLAN: dict[str, int] = {
    # must_catch = 24
    "TerminatedWithActiveAdmin": 9,
    "TerminatedWithActiveAdminUniversal": 1,
    "OrphanNoHRRecord": 5,
    "PrivilegedGrantNoTicket": 4,
    "GrantBeforeHireDate": 2,
    "DormantPrivileged": 3,
    # judgment (account-scoped) = 7
    "ContractorOverstayWithVouch": 3,
    "TransferKeptOldAccess": 2,
    "SoDConflictWithCompensatingControl": 2,
    # trap = 12
    "ApprovedServiceAccount": 3,
    "BreakGlassDormant": 2,
    "EmployeeOnLeave": 4,
    "ExemptedSoDPair": 3,
}

_CLEAN = ["CleanFTE", "CleanContractor", "CleanTransfer", "CleanPrivileged"]


def assign_narratives(population: list[Person], rng) -> list[tuple[Person, str]]:
    planted_names: list[str] = []
    for name, n in PLANTED_PLAN.items():
        planted_names.extend([name] * n)
    idx = list(range(len(population)))
    rng.shuffle(idx)
    planted_idx = set(idx[:len(planted_names)])
    rng.shuffle(planted_names)
    weights = [NARRATIVES[c].weight for c in _CLEAN]

    pairs: list[tuple[Person, str]] = []
    pi = 0
    for i, person in enumerate(population):
        if i in planted_idx:
            pairs.append((person, planted_names[pi]))
            pi += 1
        else:
            pairs.append((person, rng.choices(_CLEAN, weights=weights)[0]))
    return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cast.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/cast.py tests/test_cast.py
git commit -m "feat: cast assignment at target planted counts"
```

---

### Task 15: Deliberate messes

**Files:**
- Create: `meridian/messes.py`
- Test: `tests/test_messes.py`

**Interfaces:**
- Consumes: `Person`, `Entitlement`.
- Produces:
  - `duplicate_some_accounts(iam_rows, rng) -> list[Entitlement]` — appends a few exact-duplicate rows.
  - `drift_department_casing(hr_rows, rng) -> list[Person]` — returns HR rows where a fraction have department strings with casing/whitespace drift (e.g. `" finance & accounting "`).
  - `format_grant_date(d: date, style: str) -> str` — renders a date as `"%Y-%m-%d"` or `"%m/%d/%Y"`. (Used by the emitter to mix two date formats in the entitlements CSV.)

  The name-mismatch hazard is already produced in population/identity, so it is not re-applied here.

- [ ] **Step 1: Write the failing test** in `tests/test_messes.py`

```python
from datetime import date
from meridian.models import Entitlement, Person
from meridian.rng import make_rng
from meridian.messes import duplicate_some_accounts, drift_department_casing, format_grant_date


def _ent(aid):
    return Entitlement(aid, "a.b", "Slack", "Member", date(2025, 1, 1), "gw", None)


def test_duplicates_added():
    rows = [_ent(f"A{i}") for i in range(100)]
    out = duplicate_some_accounts(rows, make_rng(2))
    assert len(out) > len(rows)


def test_department_casing_drifts_for_some():
    people = [Person(f"E{i}", "A B", "a@b.com", "Finance & Accounting", "t",
                     date(2020, 1, 1), None, "FTE", "active", True) for i in range(100)]
    out = drift_department_casing(people, make_rng(2))
    assert any(p.department != "Finance & Accounting" for p in out)
    assert all(p.department.strip().lower() == "finance & accounting" for p in out)


def test_date_formats():
    assert format_grant_date(date(2026, 3, 4), "iso") == "2026-03-04"
    assert format_grant_date(date(2026, 3, 4), "us") == "03/04/2026"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_messes.py -v`
Expected: FAIL with `ImportError` for `meridian.messes`.

- [ ] **Step 3: Write `meridian/messes.py`**

```python
from __future__ import annotations

from dataclasses import replace
from datetime import date

from meridian.models import Entitlement, Person


def duplicate_some_accounts(iam_rows: list[Entitlement], rng) -> list[Entitlement]:
    out = list(iam_rows)
    k = max(1, len(iam_rows) // 500)
    for _ in range(k):
        out.append(rng.choice(iam_rows))
    return out


def drift_department_casing(hr_rows: list[Person], rng) -> list[Person]:
    out = []
    for p in hr_rows:
        if rng.random() < 0.05:
            variant = rng.choice([p.department.lower(), f" {p.department} ",
                                   p.department.upper()])
            out.append(replace(p, department=variant))
        else:
            out.append(p)
    return out


def format_grant_date(d: date, style: str) -> str:
    return d.strftime("%m/%d/%Y") if style == "us" else d.strftime("%Y-%m-%d")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_messes.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/messes.py tests/test_messes.py
git commit -m "feat: deliberate data messes"
```

---

### Task 16: Emitters

**Files:**
- Create: `meridian/emit.py`
- Test: `tests/test_emit.py`

**Interfaces:**
- Consumes: `Person`, `Entitlement`, `Ticket`, `PriorReviewRow`, `format_grant_date`, `World.policies_dir`.
- Produces (all take an explicit `rng` where a format choice is needed, and write into `out_dir`):
  - `write_hr_roster(path, hr_rows)` — CSV: `employee_id,full_name,email,department,title,hire_date,term_date,employment_type,status`. Orphans (not in `hr_rows`) never appear.
  - `write_entitlements(path, iam_rows, rng)` — CSV: `account_id,account_name,app,role,granted_date,granted_by,last_login`; each row's `granted_date` uses a per-row random format (`iso`/`us`); `last_login` blank when `None`.
  - `write_tickets(path, tickets)` — JSON array.
  - `write_prior_review(path, rows)` — CSV: `account_id,app,reviewer,decision,review_date`.
  - `copy_policies(src_dir, dst_dir)` — copies the policy markdown into `export_dir/policies/`.

- [ ] **Step 1: Write the failing test** in `tests/test_emit.py`

```python
import csv
import json
from datetime import date
from meridian.models import Person, Entitlement, Ticket, PriorReviewRow
from meridian.rng import make_rng
from meridian.emit import (write_hr_roster, write_entitlements, write_tickets,
                           write_prior_review)


def test_hr_roster_roundtrip(tmp_path):
    p = Person("E00001", "Bob Smith", "bob.smith@x.com", "Finance", "Clerk",
               date(2020, 1, 1), None, "FTE", "active", True)
    path = tmp_path / "hr.csv"
    write_hr_roster(str(path), [p])
    rows = list(csv.DictReader(open(path)))
    assert rows[0]["employee_id"] == "E00001"
    assert rows[0]["term_date"] == ""          # None -> blank


def test_entitlements_blank_last_login(tmp_path):
    e = Entitlement("A1", "a.b", "Slack", "Member", date(2025, 1, 1), "gw", None)
    path = tmp_path / "ent.csv"
    write_entitlements(str(path), [e], make_rng(1))
    rows = list(csv.DictReader(open(path)))
    assert rows[0]["last_login"] == ""


def test_tickets_json(tmp_path):
    t = Ticket("REQ-1", "A1", "Vault", "Admin", date(2025, 1, 1), "mgr", "approved")
    path = tmp_path / "t.json"
    write_tickets(str(path), [t])
    data = json.load(open(path))
    assert data[0]["ticket_id"] == "REQ-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_emit.py -v`
Expected: FAIL with `ImportError` for `meridian.emit`.

- [ ] **Step 3: Write `meridian/emit.py`**

```python
from __future__ import annotations

import csv
import json
import os
import shutil

from meridian.messes import format_grant_date


def _iso(d):
    return d.strftime("%Y-%m-%d") if d else ""


def write_hr_roster(path: str, hr_rows) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["employee_id", "full_name", "email", "department", "title",
                    "hire_date", "term_date", "employment_type", "status"])
        for p in hr_rows:
            w.writerow([p.employee_id, p.full_name, p.email, p.department, p.title,
                        _iso(p.hire_date), _iso(p.term_date), p.employment_type, p.status])


def write_entitlements(path: str, iam_rows, rng) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["account_id", "account_name", "app", "role", "granted_date",
                    "granted_by", "last_login"])
        for e in iam_rows:
            style = "us" if rng.random() < 0.5 else "iso"
            w.writerow([e.account_id, e.account_name, e.app, e.role,
                        format_grant_date(e.granted_date, style), e.granted_by,
                        _iso(e.last_login)])


def write_tickets(path: str, tickets) -> None:
    data = [{"ticket_id": t.ticket_id, "account_id": t.account_id, "app": t.app,
             "role": t.role, "requested_date": _iso(t.requested_date),
             "approver": t.approver, "status": t.status} for t in tickets]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def write_prior_review(path: str, rows) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["account_id", "app", "reviewer", "decision", "review_date"])
        for r in rows:
            w.writerow([r.account_id, r.app, r.reviewer, r.decision, _iso(r.review_date)])


def copy_policies(src_dir: str, dst_dir: str) -> None:
    os.makedirs(dst_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        if name.endswith(".md"):
            shutil.copyfile(os.path.join(src_dir, name), os.path.join(dst_dir, name))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_emit.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/emit.py tests/test_emit.py
git commit -m "feat: file emitters"
```

---

### Task 17: Answer key assembly

**Files:**
- Create: `meridian/answer_key.py`
- Test: `tests/test_answer_key.py`

**Interfaces:**
- Consumes: `Case`.
- Produces:
  - `build_answer_key(seed, quarter, cases, clean_count) -> dict` — assembles the key dict with `seed`, `quarter`, `counts` (by class), and `cases` (each serialized via `case_to_dict`).
  - `case_to_dict(case) -> dict`.
  - `write_answer_key(path, key) -> None`.

- [ ] **Step 1: Write the failing test** in `tests/test_answer_key.py`

```python
import json
from meridian.models import Case
from meridian.answer_key import build_answer_key, write_answer_key


def _cases():
    return [
        Case("c1", "TerminatedWithActiveAdmin", "must_catch", "account",
             {"account_id": "A1"}, {"recommendation": "revoke"}, ["term_date"]),
        Case("c2", "PriorReviewCoverageGap", "judgment", "application",
             {"app": "Box"}, {"recommendation": "review"}, ["not_in_prior_review"]),
        Case("c3", "ExemptedSoDPair", "trap", "account", {"account_id": "A2"}, {}, []),
    ]


def test_counts_tally_by_class():
    key = build_answer_key(123, "2026-Q4", _cases(), clean_count=1155)
    assert key["counts"] == {"must_catch": 1, "judgment": 1, "trap": 1, "clean": 1155}
    assert key["seed"] == 123 and key["quarter"] == "2026-Q4"


def test_write_and_reload(tmp_path):
    key = build_answer_key(123, "2026-Q4", _cases(), clean_count=1155)
    path = tmp_path / "answer_key.json"
    write_answer_key(str(path), key)
    reloaded = json.load(open(path))
    assert len(reloaded["cases"]) == 3
    assert reloaded["cases"][2]["expected"] == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_answer_key.py -v`
Expected: FAIL with `ImportError` for `meridian.answer_key`.

- [ ] **Step 3: Write `meridian/answer_key.py`**

```python
from __future__ import annotations

import json
from collections import Counter


def case_to_dict(case) -> dict:
    return {
        "case_id": case.case_id,
        "narrative": case.narrative,
        "class": case.finding_class,
        "scope": case.scope,
        "subject": case.subject,
        "expected": case.expected,
        "rationale_must_reference": case.rationale_must_reference,
    }


def build_answer_key(seed: int, quarter: str, cases, clean_count: int) -> dict:
    by_class = Counter(c.finding_class for c in cases)
    counts = {
        "must_catch": by_class.get("must_catch", 0),
        "judgment": by_class.get("judgment", 0),
        "trap": by_class.get("trap", 0),
        "clean": clean_count,
    }
    return {
        "seed": seed,
        "quarter": quarter,
        "counts": counts,
        "cases": [case_to_dict(c) for c in cases],
    }


def write_answer_key(path: str, key: dict) -> None:
    with open(path, "w") as f:
        json.dump(key, f, indent=2, sort_keys=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_answer_key.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add meridian/answer_key.py tests/test_answer_key.py
git commit -m "feat: answer key assembly"
```

---

### Task 18: CLI orchestration

**Files:**
- Create: `meridian/generate.py`
- Test: `tests/test_coherence.py` (Task 19 relies on running the CLI; this task adds a smoke test inline)

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `generate(seed: int, quarter: str, out_dir: str, key_path: str | None) -> dict` — runs the full pipeline and returns the answer-key dict. Writes all five artifacts + policies into `out_dir`, and the key to `key_path` if given.
  - `quarter_bounds(quarter: str) -> tuple[date, date]` — parses `"2026-Q3"` → `(quarter_start, quarter_end)`.
  - `main(argv=None)` — argparse CLI matching the spec's interface.
- Pipeline order: load world → `choose_apps` → build population → `assign_narratives` → for each (person, narrative) call `emit(...)` with a monotonically increasing account-id counter, collecting hr/iam/tickets/prior/cases → add `coverage_gap_cases` → override new-app entitlement grant dates to be recent (via `effective_impl_date`) → `build_prior_review` → inject messes → shuffle all exported row lists → write files → assemble & write key.

- [ ] **Step 1: Write the failing smoke test** in `tests/test_coherence.py` (coherence assertions come in Task 19; this first test just drives the CLI)

```python
import json
import os
from meridian.generate import generate


def test_generate_writes_all_artifacts(tmp_path):
    out = tmp_path / "2026-Q3"
    key = tmp_path / "answer_key.json"
    generate(20260715, "2026-Q3", str(out), str(key))
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv"]:
        assert (out / name).exists()
    assert (out / "policies" / "access-control-policy.md").exists()
    k = json.load(open(key))
    assert k["counts"]["must_catch"] == 24
    assert k["counts"]["trap"] == 13   # 12 account traps + 1 new-app trap
    assert k["counts"]["judgment"] == 9  # 7 account + 2 coverage-gap
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_coherence.py -v`
Expected: FAIL with `ImportError` for `meridian.generate`.

- [ ] **Step 3: Write `meridian/generate.py`**

```python
from __future__ import annotations

import argparse
import os
from dataclasses import replace
from datetime import date

from meridian.answer_key import build_answer_key, write_answer_key
from meridian.app_selection import choose_apps, coverage_gap_cases, effective_impl_date
from meridian.cast import assign_narratives
from meridian.emit import (copy_policies, write_entitlements, write_hr_roster,
                           write_prior_review, write_tickets)
from meridian.messes import drift_department_casing, duplicate_some_accounts
from meridian.narratives import NARRATIVES
from meridian.population import build_population
from meridian.prior_review import build_prior_review
from meridian.rng import make_faker, make_rng
from meridian.world import load_world


def quarter_bounds(quarter: str) -> tuple[date, date]:
    year_s, q_s = quarter.split("-Q")
    year, q = int(year_s), int(q_s)
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    last_day = 30 if end_month in (4, 6, 9, 11) else 31
    if end_month == 12:
        last_day = 31
    end = date(year, end_month, last_day)
    return start, end


def generate(seed: int, quarter: str, out_dir: str, key_path: str | None = None) -> dict:
    rng = make_rng(seed)
    faker = make_faker(rng)
    world = load_world("world")
    q_start, q_end = quarter_bounds(quarter)

    selection = choose_apps(world, rng)
    population = build_population(world, rng, faker, q_end)
    pairs = assign_narratives(population, rng)

    hr_rows, iam_rows, tickets, prior_narrative, cases = [], [], [], [], []
    counter = 1
    for person, narrative_name in pairs:
        account_id = f"A{counter:06d}"
        counter += 1
        result = NARRATIVES[narrative_name].emit(person, world, rng, faker, q_end, account_id)
        hr_rows.extend(result.hr_rows)
        iam_rows.extend(result.iam_rows)
        tickets.extend(result.tickets)
        prior_narrative.extend(result.prior_review_rows)
        cases.extend(result.cases)

    cases.extend(coverage_gap_cases(selection))

    # make the new app look freshly rolled out: recent grant dates
    new_grant = effective_impl_date(selection.new_app, selection, world, q_start)
    iam_rows = [replace(e, granted_date=new_grant) if e.app == selection.new_app else e
                for e in iam_rows]

    prior_rows = build_prior_review(iam_rows, selection, prior_narrative, rng, q_end)

    # deliberate messes
    iam_rows = duplicate_some_accounts(iam_rows, rng)
    hr_rows = drift_department_casing(hr_rows, rng)

    # shuffle every exported list so order encodes nothing
    for lst in (hr_rows, iam_rows, tickets, prior_rows):
        rng.shuffle(lst)

    os.makedirs(out_dir, exist_ok=True)
    write_hr_roster(os.path.join(out_dir, "hr_roster.csv"), hr_rows)
    write_entitlements(os.path.join(out_dir, "entitlements.csv"), iam_rows, rng)
    write_tickets(os.path.join(out_dir, "access_tickets.json"), tickets)
    write_prior_review(os.path.join(out_dir, "prior_review.csv"), prior_rows)
    copy_policies(world.policies_dir, os.path.join(out_dir, "policies"))

    clean_count = sum(1 for _p, n in pairs if NARRATIVES[n].finding_class == "clean")
    key = build_answer_key(seed, quarter, cases, clean_count)
    if key_path:
        write_answer_key(key_path, key)
    return key


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="meridian.generate")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--quarter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default=None)
    args = ap.parse_args(argv)
    generate(args.seed, args.quarter, args.out, args.key)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_coherence.py::test_generate_writes_all_artifacts -v`
Expected: PASS (1 passed).

Note: the trap count is **13** (locked) — 12 account-scoped trap narratives + 1 application-scoped new-app trap — and judgment is **9** (7 account + 2 coverage-gap). The counts test in Task 19 asserts exactly these.

- [ ] **Step 5: Commit**

```bash
git add meridian/generate.py tests/test_coherence.py
git commit -m "feat: CLI orchestration pipeline"
```

---

### Task 19: Coherence, determinism, anti-leak & counts tests

**Files:**
- Modify: `tests/test_coherence.py`
- Create: `tests/test_acceptance.py`

**Interfaces:**
- Consumes: `generate`, the emitted files, the answer key.
- This task adds no production code — it is the acceptance gate. **Coherence is the load-bearing test: every keyed case must be genuinely derivable from the emitted artifacts.**

- [ ] **Step 1: Add coherence assertions** to `tests/test_coherence.py`

```python
import csv
import json


def _load(out):
    hr = list(csv.DictReader(open(out / "hr_roster.csv")))
    ent = list(csv.DictReader(open(out / "entitlements.csv")))
    prior = list(csv.DictReader(open(out / "prior_review.csv")))
    return hr, ent, prior


def test_coherence_every_case_derivable(tmp_path):
    out = tmp_path / "2026-Q3"
    key_path = tmp_path / "answer_key.json"
    key = __import__("meridian.generate", fromlist=["generate"]).generate(
        20260715, "2026-Q3", str(out), str(key_path))
    hr, ent, prior = _load(out)
    hr_by_id = {r["employee_id"]: r for r in hr}
    ent_by_acct = {}
    for r in ent:
        ent_by_acct.setdefault(r["account_id"], []).append(r)
    prior_apps = {r["app"] for r in prior}

    for case in key["cases"]:
        subj = case["subject"]
        if case["narrative"] == "TerminatedWithActiveAdmin" or \
           case["narrative"] == "TerminatedWithActiveAdminUniversal":
            # HR row shows a term date; the flagged entitlement still exists
            row = hr_by_id[subj["employee_id"]]
            assert row["term_date"] != "", "terminated case must have a term_date"
            assert subj["account_id"] in ent_by_acct
        elif case["narrative"] == "OrphanNoHRRecord":
            assert subj["employee_id"] in (None, "")
            assert subj["account_id"] in ent_by_acct   # entitlements exist, HR does not
        elif case["narrative"] == "PriorReviewCoverageGap":
            assert subj["app"] not in prior_apps       # genuinely absent from prior review
        elif case["narrative"] == "NewAppNoPriorReview":
            assert subj["app"] not in prior_apps       # the trap: also absent, but expected
```

- [ ] **Step 2: Run coherence test**

Run: `pytest tests/test_coherence.py -v`
Expected: PASS. If any case fails to derive, **the generator is wrong, not the test** — fix the emitting narrative.

- [ ] **Step 3: Write `tests/test_acceptance.py`** (determinism, anti-leak, counts)

```python
import csv
import filecmp
import os
from collections import Counter

from meridian.generate import generate


def _gen(tmp, seed=20260715, quarter="2026-Q3"):
    out = tmp / quarter
    key = tmp / "answer_key.json"
    generate(seed, quarter, str(out), str(key))
    return out, key


def test_determinism_byte_identical(tmp_path):
    a, ka = _gen(tmp_path / "a")
    b, kb = _gen(tmp_path / "b")
    for name in ["hr_roster.csv", "entitlements.csv", "access_tickets.json",
                 "prior_review.csv"]:
        assert filecmp.cmp(a / name, b / name, shallow=False), f"{name} differs"
    assert open(ka).read() == open(kb).read()


def test_counts_hit_targets(tmp_path):
    import json
    _out, key = _gen(tmp_path)
    k = json.load(open(key))
    assert k["counts"]["must_catch"] == 24
    assert k["counts"]["judgment"] == 9
    assert k["counts"]["trap"] == 13


def test_anti_leak_planted_ids_not_clustered(tmp_path):
    import json
    out, key = _gen(tmp_path)
    k = json.load(open(key))
    planted_accts = [c["subject"].get("account_id") for c in k["cases"]
                     if c["subject"].get("account_id")]
    nums = sorted(int(a[1:]) for a in planted_accts)
    # planted account ids should span a wide range, not sit in one contiguous block
    assert nums[-1] - nums[0] > len(nums) * 5


def test_seed_variation_changes_selection(tmp_path):
    import json
    _o1, k1 = _gen(tmp_path / "s1", seed=1)
    _o2, k2 = _gen(tmp_path / "s2", seed=2)
    apps1 = {c["subject"]["app"] for c in json.load(open(k1))["cases"]
             if c["narrative"] == "PriorReviewCoverageGap"}
    apps2 = {c["subject"]["app"] for c in json.load(open(k2))["cases"]
             if c["narrative"] == "PriorReviewCoverageGap"}
    assert apps1 != apps2
```

- [ ] **Step 4: Run the acceptance suite**

Run: `pytest tests/test_acceptance.py -v`
Expected: PASS (4 passed). If `test_seed_variation_changes_selection` is flaky across adjacent seeds, widen the seed gap — the selection is genuinely seed-varied.

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add tests/test_coherence.py tests/test_acceptance.py
git commit -m "test: coherence, determinism, anti-leak, and counts acceptance gates"
```

---

## Self-Review Notes

- **Spec coverage:** fixed world (Task 3), narratives per class (Tasks 8–11), cast at target counts (Task 14), coverage-gap challenge + seed-varied app selection (Task 12), stubbed prior review with omissions (Task 13), deliberate messes (Task 15), CSV/JSON output + policies copy (Task 16), answer key with `scope` (Task 17), CLI + determinism (Task 18), the four required tests (Tasks 18–19). All spec sections map to a task.
- **Count reconciliation (locked):** 13 traps = 12 account-scoped trap narratives + 1 application-scoped new-app trap; 9 judgment = 7 account-scoped + 2 coverage-gap; 24 must_catch. 46 planted total. Tasks 18/19 assert exactly these.
- **Anti-leak caveat:** the plan enforces spread and shuffling. The `test_anti_leak_planted_ids_not_clustered` check is a coarse guard; a stronger statistical check can be added if a reviewer wants one.
- **Open item still open:** Faker vs. committed name list — locked to Faker in Global Constraints; revisit only if determinism proves fragile across Faker versions (pin the version in `pyproject.toml` if so).
