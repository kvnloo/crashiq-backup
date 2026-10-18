from datetime import date

import pytest

from crashiq import study


@pytest.fixture
def clock(monkeypatch):
    def set_today(d: date):
        monkeypatch.setattr(study, "today", lambda: d)
    set_today(date(2026, 10, 18))
    return set_today


@pytest.mark.parametrize("on,expected", [
    (date(2026, 10, 18), (2021, 2025)),
    (date(2026, 1, 1), (2021, 2025)),     # Jan 1: 2025 is the last complete year
    (date(2025, 12, 31), (2020, 2024)),
])
def test_default_window(on, expected):
    assert study.default_window(on) == expected


def test_default_window_never_includes_current_year(clock):
    fy, ty = study.default_window()
    assert ty == 2025 and fy == 2021


@pytest.mark.parametrize("fy,ty,msg", [
    (2015, 2019, "starts in 2016"),
    (2016, 2027, "can't end after 2026"),
    (2014, 2025, "starts in 2016"),
    (2017, 2016, "not be after"),
])
def test_window_rules(clock, fy, ty, msg):
    with pytest.raises(ValueError, match=msg):
        study.validate_window(fy, ty)


def test_window_length_limits(clock):
    study.validate_window(2025, 2025)            # 1 year ok
    study.validate_window(2016, 2025)            # 10 years ok
    with pytest.raises(ValueError, match="between 1 and 10"):
        study.validate_window(2016, 2026)        # 11 years


def test_covid_flag():
    assert study.covid_in_window(2018, 2022)
    assert study.covid_in_window(2020, 2020)
    assert not study.covid_in_window(2021, 2025)
    assert not study.covid_in_window(2016, 2019)


def test_window_options_stop_at_2016(clock):
    opts = study.window_options()
    assert [o["years"] for o in opts] == list(range(1, 11))
    assert opts[4]["label"] == "Last 5 complete years (2021–2025)"
    assert opts[0]["label"] == "Last 1 complete year (2025)"
    assert opts[-1]["from_year"] == 2016
    on_2020 = study.window_options(date(2020, 6, 1))   # last complete 2019 → only 4 options reach back to 2016
    assert [o["years"] for o in on_2020] == [1, 2, 3, 4]


def test_api_round_trip(client, clock):
    r = client.post("/api/studies", json={"name": "Crenshaw Blvd safety", "mode": "tis"})
    assert r.status_code == 201
    s = r.json()
    assert (s["from_year"], s["to_year"], s["covid_years_in_window"]) == (2021, 2025, False)
    assert s["mode_label"] == "Traffic-study safety section"
    got = client.get(f"/api/studies/{s['id']}").json()
    assert got["name"] == "Crenshaw Blvd safety"
    p = client.patch(f"/api/studies/{s['id']}", json={"from_year": 2018, "to_year": 2022}).json()
    assert p["covid_years_in_window"] is True and p["years"] == 5


def test_api_rejects_bad_input(client, clock):
    assert client.post("/api/studies", json={"name": "x", "mode": "hsip"}).status_code == 422
    assert client.post("/api/studies", json={"name": " ", "mode": "profile"}).status_code == 422
    r = client.post("/api/studies", json={"name": "x", "mode": "profile", "from_year": 2010, "to_year": 2014})
    assert r.status_code == 422 and "2016" in r.json()["detail"]
    assert client.get("/api/studies/nope").status_code == 404


def test_meta_lists_exactly_the_two_v1_modes(client, clock):
    m = client.get("/api/studies/meta").json()
    assert [x["id"] for x in m["modes"]] == ["profile", "tis"]
    assert m["default_window"] == {"from_year": 2021, "to_year": 2025}
