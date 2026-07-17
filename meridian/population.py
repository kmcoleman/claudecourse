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
            full, account, email = make_identity(faker, rng, mismatch=mismatch)
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
                account_name=account,          # carry the (possibly mismatched) IAM name
            ))
    rng.shuffle(people)                              # ID order must not encode department
    from dataclasses import replace
    return [replace(p, employee_id=f"E{i + 1:05d}") for i, p in enumerate(people)]
