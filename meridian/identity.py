from __future__ import annotations

import re

DOMAIN = "meridian-energy.com"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z]+", ".", name.lower()).strip(".")


def email_for(full_name: str) -> str:
    return f"{_slug(full_name)}@{DOMAIN}"


def make_identity(faker, rng, mismatch: bool = False) -> tuple[str, str, str]:
    full = faker.name()
    # strip any Faker prefixes/suffixes to keep names two-part and clean
    parts = [p for p in full.split() if p.isalpha()]
    if len(parts) < 2:
        parts = [faker.first_name(), faker.last_name()]
    first, last = parts[0], parts[-1]
    full = f"{first} {last}"
    email = email_for(full)
    if mismatch:
        style = rng.choice(["initial_last", "first_initial", "nickname"])
        if style == "initial_last":
            account = f"{first[0].lower()}{last.lower()}"
        elif style == "first_initial":
            account = f"{first.lower()}{last[0].lower()}"
        else:
            account = f"{faker.first_name().lower()}.{last.lower()}"
    else:
        account = f"{first.lower()}.{last.lower()}"
    return full, account, email
