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
        ents = [e for e in ents if e.app != "Atlas ERP"]   # narrative owns Atlas access; no baseline Atlas leak
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
