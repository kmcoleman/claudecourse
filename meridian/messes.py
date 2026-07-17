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
