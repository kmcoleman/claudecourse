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
        # floor at hire_date: only GrantBeforeHireDate may predate the hire
        granted = max(person.hire_date,
                      quarter_end - timedelta(days=rng.randint(60, 400)))
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
