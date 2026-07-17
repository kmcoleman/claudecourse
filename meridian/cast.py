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
