from datetime import date
from meridian.world import load_world


def test_world_loads_all_apps_and_departments():
    w = load_world("world")
    assert len(w.apps) == 22
    assert sum(w.departments.values()) == 1200
    assert "Atlas ERP" in w.apps


def test_app_fields_parsed():
    w = load_world("world")
    atlas = w.apps["Atlas ERP"]
    assert atlas.tier == "crown"
    assert "Vendor Admin" in atlas.privileged_roles
    assert isinstance(atlas.implementation_date, date)


def test_sod_exemption_present():
    w = load_world("world")
    assert any(e["clause"] == "ACP-4.2" for e in w.sod_exemptions)
