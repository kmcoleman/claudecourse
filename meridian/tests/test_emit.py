import csv
import json
from datetime import date
from meridian.models import Person, Entitlement, Ticket, PriorReviewRow
from meridian.rng import make_rng
from meridian.emit import (write_hr_roster, write_entitlements, write_tickets,
                           write_prior_review)


def test_hr_roster_roundtrip(tmp_path):
    p = Person("E00001", "Bob Smith", "bob.smith@x.com", "Finance", "Clerk",
               date(2020, 1, 1), None, "FTE", "active", True)
    path = tmp_path / "hr.csv"
    write_hr_roster(str(path), [p])
    rows = list(csv.DictReader(open(path)))
    assert rows[0]["employee_id"] == "E00001"
    assert rows[0]["term_date"] == ""          # None -> blank


def test_entitlements_blank_last_login(tmp_path):
    e = Entitlement("A1", "a.b", "Slack", "Member", date(2025, 1, 1), "gw", None)
    path = tmp_path / "ent.csv"
    write_entitlements(str(path), [e], make_rng(1))
    rows = list(csv.DictReader(open(path)))
    assert rows[0]["last_login"] == ""


def test_tickets_json(tmp_path):
    t = Ticket("REQ-1", "A1", "Vault", "Admin", date(2025, 1, 1), "mgr", "approved")
    path = tmp_path / "t.json"
    write_tickets(str(path), [t])
    data = json.load(open(path))
    assert data[0]["ticket_id"] == "REQ-1"
