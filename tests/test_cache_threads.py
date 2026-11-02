"""#323 (Tester): the Caltrans postmile and AADT caches shared one SQLite connection across the server's worker threads
with no lock (check_same_thread=False). Tab 3 of a state-highway study asks for the profile, the crash list and the
assignment at once; on a live I-405 study 2-3 of every 6 parallel requests failed (500: "bad parameter or other API
misuse", IndexError on a short row, None coordinates). Lookups from several threads at once must give the same answers
as one thread, with no errors."""

import threading

from test_aadt import cache as aadt_cache  # noqa: F401  (the 2024 LA-405 / ORA-1 workbook fixture)
from test_postmile import cache, points  # noqa: F401  (the LA-405 fixture cache)


def hammer(calls, want, n=16, rounds=40):
    errors, wrong, go = [], [], threading.Barrier(n)

    def work():
        go.wait()
        for _ in range(rounds):
            for f, w in zip(calls, want):
                try:
                    if f() != w:
                        wrong.append(w)
                except Exception as e:      # noqa: BLE001  (any error is the bug)
                    errors.append(repr(e))

    ts = [threading.Thread(target=work) for _ in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return errors, wrong


def test_postmile_lookups_from_many_threads_at_once_match_one_thread(cache):  # noqa: F811
    calls = [lambda lat=lat, lon=lon: cache.lookup(lat, lon, {"405"}, "N") for _, lat, lon in points("405", "NB")[2:40]]
    want = [f() for f in calls]
    errors, wrong = hammer(calls, want)
    assert not errors and not wrong, f"{len(errors)} errors, {len(wrong)} wrong answers; first: {errors[:2]}"


def test_aadt_lookups_from_many_threads_at_once_match_one_thread(aadt_cache):  # noqa: F811
    c = aadt_cache
    calls = [lambda pm=pm: c.segment("405", "LA", pm, year=2024) for pm in (13.3, 13.5, 13.9, 14.2, 15.0, 16.1)]
    calls += [lambda pm=pm: c.truck_segment("1", "ORA", pm, year=2024) for pm in (0.2, 0.5, 0.9)]
    calls += [lambda: [y for (y,) in c.db().execute("SELECT DISTINCT year FROM point ORDER BY year")]]
    want = [f() for f in calls]
    assert any(want)
    errors, wrong = hammer(calls, want)
    assert not errors and not wrong, f"{len(errors)} errors, {len(wrong)} wrong answers; first: {errors[:2]}"


def test_the_fake_ckan_answers_many_threads_at_once():
    from crashiq.sources.fake_ckan import FakeCkan
    from conftest import FIXTURES
    fk = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    rid = next(iter(fk.tables))
    sql = {"sql": f'SELECT COUNT(*) AS n FROM "{rid}"'}
    calls = [lambda: fk("datastore_search_sql", sql)] * 5
    want = [f() for f in calls]
    errors, wrong = hammer(calls, want, rounds=60)
    assert not errors and not wrong, f"{len(errors)} errors, {len(wrong)} wrong answers; first: {errors[:2]}"
