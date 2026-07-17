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
                                max(person.hire_date,
                                    quarter_end - timedelta(days=400)),
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
                                max(person.hire_date,
                                    quarter_end - timedelta(days=rng.randint(30, 300))),
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
        # the whole account has gone dark, not just the privileged grant: push
        # every existing last_login on this account back beyond 180 days so the
        # dormancy finding is true of the account, not an isolated data point
        for e in ents:
            if e.last_login is not None:
                e.last_login = quarter_end - timedelta(days=rng.randint(200, 400))
        app, role = "Vault", "Admin"
        ents.append(_priv_grant(account_id, name, app, role,
                                max(person.hire_date,
                                    quarter_end - timedelta(days=500)),
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
