import json
from datetime import date
from meridian.world import load_world
from meridian.rng import make_rng
from meridian.app_selection import choose_apps
from meridian.emit import write_applications, write_sod_matrix, write_service_accounts


def _world_and_selection(seed=20260715):
    w = load_world("world")
    sel = choose_apps(w, make_rng(seed))
    return w, sel


def test_applications_has_all_apps_and_new_app_is_in_quarter(tmp_path):
    w, sel = _world_and_selection()
    q_start = date(2026, 7, 1)
    path = tmp_path / "applications.json"
    write_applications(str(path), w, sel, q_start)
    apps = json.load(open(path))
    assert len(apps) == len(w.apps) == 22
    by_name = {a["name"]: a for a in apps}
    # every record has the required fields
    for a in apps:
        assert set(a) == {"name", "tier", "roles", "privileged_roles",
                          "owning_dept", "implementation_date"}
    # the new app's effective implementation_date is inside the quarter
    new_date = date.fromisoformat(by_name[sel.new_app]["implementation_date"])
    assert new_date >= q_start


def test_sod_matrix_shape(tmp_path):
    w, _sel = _world_and_selection()
    path = tmp_path / "sod_matrix.json"
    write_sod_matrix(str(path), w)
    data = json.load(open(path))
    assert set(data) == {"conflicts", "exemptions"}
    assert any(e.get("clause") == "ACP-4.2" for e in data["exemptions"])


def test_service_accounts_is_list_with_known_members(tmp_path):
    w, _sel = _world_and_selection()
    path = tmp_path / "service_accounts.json"
    write_service_accounts(str(path), w)
    data = json.load(open(path))
    assert isinstance(data, list)
    assert "marcus.pipeline" in data and "emergency.admin" in data
