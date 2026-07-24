"""Meridian systems MCP server (read-only).

Course simplification: a real client would expose HR, identity, and ITSM as
separate connectors; this collapses them into one server for setup simplicity.
Configure the data directory via MERIDIAN_DATA_DIR (default data/2026-Q3).
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def data_dir() -> Path:
    return Path(os.environ.get("MERIDIAN_DATA_DIR", "data/2026-Q3"))


def _read_csv(d: Path, name: str) -> list[dict]:
    with open(d / name, newline="") as f:
        return list(csv.DictReader(f))


def _read_json(d: Path, name: str):
    with open(d / name) as f:
        return json.load(f)


# --- plain implementations (directly unit-tested) ---

def _get_employee(d: Path, employee_id: str) -> dict | None:
    for row in _read_csv(d, "hr_roster.csv"):
        if row["employee_id"] == employee_id:
            return row
    return None


def _get_account(d: Path, account_id: str) -> dict | None:
    ents = [r for r in _read_csv(d, "entitlements.csv") if r["account_id"] == account_id]
    if not ents:
        return None
    return {"account_id": account_id,
            "account_name": ents[0]["account_name"],
            "entitlements": [{k: r[k] for k in
                              ("app", "role", "granted_date", "granted_by", "last_login")}
                             for r in ents]}


def _search_tickets(d: Path, account_id: str, app: str | None = None) -> list[dict]:
    out = [t for t in _read_json(d, "access_tickets.json")
           if t["account_id"] == account_id and (app is None or t["app"] == app)]
    return out


def _get_prior_review(d: Path, account_id: str) -> list[dict]:
    return [r for r in _read_csv(d, "prior_review.csv") if r["account_id"] == account_id]


def _get_application(d: Path, app_name: str) -> dict | None:
    for a in _read_json(d, "applications.json"):
        if a["name"] == app_name:
            return a
    return None


def _is_approved_service_account(d: Path, name: str) -> bool:
    return name in _read_json(d, "service_accounts.json")


def _get_sod_matrix(d: Path) -> dict:
    return _read_json(d, "sod_matrix.json")


# --- MCP tool wrappers (thin; use the env-configured data dir) ---

mcp = FastMCP("meridian-systems")


@mcp.tool()
def get_employee(employee_id: str) -> dict | None:
    """HR record for an employee, or null if none exists (the orphan signal)."""
    return _get_employee(data_dir(), employee_id)


@mcp.tool()
def get_account(account_id: str) -> dict | None:
    """IAM view of one account: account_name and its entitlement rows."""
    return _get_account(data_dir(), account_id)


@mcp.tool()
def search_tickets(account_id: str, app: str | None = None) -> list:
    """Access-request tickets for an account, optionally filtered by app."""
    return _search_tickets(data_dir(), account_id, app)


@mcp.tool()
def get_prior_review(account_id: str) -> list:
    """Last quarter's review decisions for an account (empty if none)."""
    return _get_prior_review(data_dir(), account_id)


@mcp.tool()
def get_application(app_name: str) -> dict | None:
    """App catalog entry: tier, implementation_date, roles, privileged_roles, owning_dept."""
    return _get_application(data_dir(), app_name)


@mcp.tool()
def is_approved_service_account(name: str) -> bool:
    """True if the account name is in the approved service-account registry."""
    return _is_approved_service_account(data_dir(), name)


@mcp.tool()
def get_sod_matrix() -> dict:
    """Structured SoD conflict pairs and documented exemptions."""
    return _get_sod_matrix(data_dir())


if __name__ == "__main__":
    mcp.run()
