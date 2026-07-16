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
    account_name: str = ""  # IAM-side display name; may mismatch full_name (~10% hazard).
                            # Defaulted last so 10-arg positional construction still works.


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
