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
