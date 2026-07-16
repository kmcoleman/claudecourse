from __future__ import annotations

from meridian.entitlements import baseline_entitlements
from meridian.models import EmitResult, Person, World


class Narrative:
    name: str = "Narrative"
    finding_class: str = "clean"
    weight: float = 0.0

    def emit(self, person: Person, world: World, rng, faker, quarter_end,
             account_id: str) -> EmitResult:
        ents = baseline_entitlements(person, world, rng, faker, quarter_end, account_id)
        return EmitResult(hr_rows=[person], iam_rows=ents)
