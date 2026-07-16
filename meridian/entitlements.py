from __future__ import annotations

from datetime import date, timedelta

from meridian.models import Entitlement, Person, World

_UNIVERSAL = ["Slack", "Zoom", "VPN", "Badge access"]
# org-wide business tools nearly everyone holds
_COMMON_BUSINESS = ["PeopleHub HRIS", "Expense", "Box", "DocuSign"]
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
# accumulated miscellaneous access (realistic sprawl); adds volume toward ~12.5/person
_EXTRA_POOL = ["Tableau", "Jenkins", "Snowflake", "Compass CRM", "Helix ITSM", "AWS NonProd"]


def account_name_for(person: Person, rng=None, faker=None) -> str:
    # the IAM-side name carries the mismatch hazard, set at population time
    if person.account_name:
        return person.account_name
    parts = person.full_name.split()
    return f"{parts[0].lower()}.{parts[-1].lower()}"


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
    account_name = account_name_for(person)
    ents: list[Entitlement] = []
    granted_apps: set[str] = set()

    def add(app, role):
        ents.append(_grant(app, role, person, rng, quarter_end, account_id, account_name))
        granted_apps.add(app)

    # universal apps + core directory/IdP — everyone
    for app in _UNIVERSAL:
        add(app, world.apps[app].roles[0])
    add("Active Directory", "Standard")
    add("Gateway", "Help Desk")
    # org-wide business tools — everyone
    for app in _COMMON_BUSINESS:
        add(app, world.apps[app].roles[0])
    # department-appropriate apps — at most one grant per app per person, and
    # baseline never hands out a privileged/SoD-relevant role (those come only
    # from the narrative layer in later tasks).
    for app in _DEPT_APPS.get(person.department, []):
        if app in granted_apps:
            continue
        if rng.random() < 0.75:
            spec = world.apps[app]
            non_privileged = [r for r in spec.roles if r not in spec.privileged_roles]
            if not non_privileged:
                continue
            add(app, rng.choice(non_privileged))
    # accumulated sprawl — skip apps already held, and never sample more apps
    # than are actually available to add
    sprawl_candidates = [app for app in _EXTRA_POOL if app not in granted_apps]
    sample_size = min(rng.randint(0, 3), len(sprawl_candidates))
    for app in rng.sample(sprawl_candidates, sample_size):
        role = world.apps[app].roles[0]
        # defensive: sprawl/common-business pools are expected to use only the
        # base (non-privileged) role — baseline must never grant privileged access
        assert role not in world.apps[app].privileged_roles, (
            f"sprawl base role {role!r} for {app!r} is privileged"
        )
        add(app, role)
    return ents
