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
        # The narrative owns this account's Atlas access. Strip any baseline Atlas role
        # first: otherwise a baseline "AP Clerk" would give the Controller a genuine,
        # NON-exempt AP Clerk+AP Manager conflict, making this "don't flag" trap actually
        # flaggable. After stripping, Atlas roles are exactly the exempted pair.
        ents = [e for e in ents if e.app != "Atlas ERP"]
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
