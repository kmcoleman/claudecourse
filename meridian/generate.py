from __future__ import annotations

import argparse
import os
from dataclasses import replace
from datetime import date

from meridian.answer_key import build_answer_key, write_answer_key
from meridian.app_selection import choose_apps, coverage_gap_cases, effective_impl_date
from meridian.cast import assign_narratives
from meridian.emit import (copy_policies, write_applications, write_entitlements,
                           write_hr_roster, write_prior_review, write_service_accounts,
                           write_sod_matrix, write_tickets)
from meridian.messes import drift_department_casing, duplicate_some_accounts
from meridian.narratives import NARRATIVES
from meridian.population import build_population
from meridian.prior_review import build_prior_review
from meridian.rng import make_faker, make_rng
from meridian.world import load_world


def quarter_bounds(quarter: str) -> tuple[date, date]:
    year_s, q_s = quarter.split("-Q")
    year, q = int(year_s), int(q_s)
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    last_day = 30 if end_month in (4, 6, 9, 11) else 31
    if end_month == 12:
        last_day = 31
    end = date(year, end_month, last_day)
    return start, end


def generate(seed: int, quarter: str, out_dir: str, key_path: str | None = None) -> dict:
    rng = make_rng(seed)
    faker = make_faker(rng)
    world = load_world("world")
    q_start, q_end = quarter_bounds(quarter)

    selection = choose_apps(world, rng)
    population = build_population(world, rng, faker, q_end)
    pairs = assign_narratives(population, rng)

    hr_rows, iam_rows, tickets, prior_narrative, cases = [], [], [], [], []
    hire_by_account: dict[str, date] = {}
    counter = 1
    for person, narrative_name in pairs:
        account_id = f"A{counter:06d}"
        counter += 1
        hire_by_account[account_id] = person.hire_date
        result = NARRATIVES[narrative_name].emit(person, world, rng, faker, q_end, account_id)
        hr_rows.extend(result.hr_rows)
        iam_rows.extend(result.iam_rows)
        tickets.extend(result.tickets)
        prior_narrative.extend(result.prior_review_rows)
        cases.extend(result.cases)

    cases.extend(coverage_gap_cases(selection))

    # make the new app look freshly rolled out: recent grant dates. Floor each
    # rewritten date at the holder's hire_date so the rollout (quarter_start+20)
    # never precedes the hire of anyone onboarded in the last ~70 days -- that
    # would manufacture an unplanted grant-before-hire finding.
    new_grant = effective_impl_date(selection.new_app, selection, world, q_start)
    iam_rows = [replace(e, granted_date=max(new_grant,
                                            hire_by_account.get(e.account_id, new_grant)))
                if e.app == selection.new_app else e
                for e in iam_rows]

    prior_rows = build_prior_review(iam_rows, selection, prior_narrative, rng, q_end)

    # deliberate messes
    iam_rows = duplicate_some_accounts(iam_rows, rng)
    hr_rows = drift_department_casing(hr_rows, rng)

    # shuffle every exported list so order encodes nothing
    for lst in (hr_rows, iam_rows, tickets, prior_rows):
        rng.shuffle(lst)

    os.makedirs(out_dir, exist_ok=True)
    write_hr_roster(os.path.join(out_dir, "hr_roster.csv"), hr_rows)
    write_entitlements(os.path.join(out_dir, "entitlements.csv"), iam_rows, rng)
    write_tickets(os.path.join(out_dir, "access_tickets.json"), tickets)
    write_prior_review(os.path.join(out_dir, "prior_review.csv"), prior_rows)
    copy_policies(world.policies_dir, os.path.join(out_dir, "policies"))
    write_applications(os.path.join(out_dir, "applications.json"), world, selection, q_start)
    write_sod_matrix(os.path.join(out_dir, "sod_matrix.json"), world)
    write_service_accounts(os.path.join(out_dir, "service_accounts.json"), world)

    clean_count = sum(1 for _p, n in pairs if NARRATIVES[n].finding_class == "clean")
    key = build_answer_key(seed, quarter, cases, clean_count)
    if key_path:
        write_answer_key(key_path, key)
    return key


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="meridian.generate")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--quarter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default=None)
    args = ap.parse_args(argv)
    generate(args.seed, args.quarter, args.out, args.key)


if __name__ == "__main__":
    main()
