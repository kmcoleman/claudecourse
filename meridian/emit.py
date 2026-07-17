from __future__ import annotations

import csv
import json
import os
import shutil

from meridian.messes import format_grant_date


def _iso(d):
    return d.strftime("%Y-%m-%d") if d else ""


def write_hr_roster(path: str, hr_rows) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["employee_id", "full_name", "email", "department", "title",
                    "hire_date", "term_date", "employment_type", "status"])
        for p in hr_rows:
            w.writerow([p.employee_id, p.full_name, p.email, p.department, p.title,
                        _iso(p.hire_date), _iso(p.term_date), p.employment_type, p.status])


def write_entitlements(path: str, iam_rows, rng) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["account_id", "account_name", "app", "role", "granted_date",
                    "granted_by", "last_login"])
        for e in iam_rows:
            style = "us" if rng.random() < 0.5 else "iso"
            w.writerow([e.account_id, e.account_name, e.app, e.role,
                        format_grant_date(e.granted_date, style), e.granted_by,
                        _iso(e.last_login)])


def write_tickets(path: str, tickets) -> None:
    data = [{"ticket_id": t.ticket_id, "account_id": t.account_id, "app": t.app,
             "role": t.role, "requested_date": _iso(t.requested_date),
             "approver": t.approver, "status": t.status} for t in tickets]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def write_prior_review(path: str, rows) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["account_id", "app", "reviewer", "decision", "review_date"])
        for r in rows:
            w.writerow([r.account_id, r.app, r.reviewer, r.decision, _iso(r.review_date)])


def copy_policies(src_dir: str, dst_dir: str) -> None:
    os.makedirs(dst_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        if name.endswith(".md"):
            shutil.copyfile(os.path.join(src_dir, name), os.path.join(dst_dir, name))
