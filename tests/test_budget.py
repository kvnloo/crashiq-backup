import logging

import pytest

from crashiq.budget import Budget, BudgetExceeded, NoPrice, Usage, load_prices

PRICES = {"models": {"claude-x": {"provider": "claude", "input": 3.0, "output": 15.0, "cache_read": 0.3},
                     "jev-1.13.0": {"provider": "jev", "input": 0.042, "output": 0.0},
                     "claude-unpriced": {"provider": "claude", "input": None, "output": None}}}


def B(db, cap=0.10):
    return Budget(db, "s1", cap, PRICES)


def ok(i, o, result="r"):
    return lambda: (result, Usage(i, o))


def test_cost_from_the_price_table(db):
    b = B(db)
    assert b.cost("claude-x", Usage(1_000_000, 0)) == pytest.approx(3.0)
    assert b.cost("claude-x", Usage(10_000, 2_000)) == pytest.approx(0.03 + 0.03)
    assert b.cost("claude-x", Usage(10_000, 0, cache_read_tokens=8_000)) == pytest.approx((2_000 * 3 + 8_000 * 0.3) / 1e6)
    assert b.cost("jev-1.13.0", Usage(1_000_000, 500)) == pytest.approx(0.042)


def test_totals_match_the_sum_of_calls(db):
    b = B(db, cap=1.0)
    for i, o in [(5_000, 500), (8_000, 1_000), (1_000, 100)]:
        b.call(provider="claude", model="claude-x", step="findings", est_input_tokens=i, max_output_tokens=o, fn=ok(i, o))
    expected = sum((i * 3 + o * 15) / 1e6 for i, o in [(5_000, 500), (8_000, 1_000), (1_000, 100)])
    assert b.spent() == pytest.approx(expected)
    rep = b.report()
    assert rep["spent_usd"] == pytest.approx(expected, abs=1e-6) and rep["by_step"][0]["calls"] == 3


def test_cap_hit_mid_run_refuses_before_calling(db):
    b = B(db, cap=0.10)
    called = []

    def fn():
        called.append(1)
        return "r", Usage(10_000, 2_000)        # $0.06 each

    b.call(provider="claude", model="claude-x", step="findings", est_input_tokens=10_000, max_output_tokens=2_000, fn=fn)
    with pytest.raises(BudgetExceeded, match=r"\$0\.10"):
        b.call(provider="claude", model="claude-x", step="findings", est_input_tokens=10_000, max_output_tokens=2_000, fn=fn)
    assert len(called) == 1                        # the second call never reached the provider
    assert b.spent() == pytest.approx(0.06)


def test_fallback_when_over_cap_or_provider_down(db):
    b = B(db, cap=0.001)
    out, fell = b.call_or_fallback(lambda: "review queue", provider="claude", model="claude-x", step="findings",
                                   est_input_tokens=10_000, max_output_tokens=2_000, fn=ok(1, 1))
    assert (out, fell) == ("review queue", True)

    def boom():
        raise ConnectionError("api.anthropic.com unreachable")
    b2 = B(db, cap=1.0)
    out, fell = b2.call_or_fallback(lambda: "profile only", provider="claude", model="claude-x", step="findings",
                                    est_input_tokens=100, max_output_tokens=100, fn=boom)
    assert (out, fell) == ("profile only", True)
    outcomes = [r["outcome"] for r in db.query("SELECT outcome FROM ai_spend ORDER BY id")]
    assert outcomes == ["refused_over_cap", "fallback", "error", "fallback"]


def test_unpriced_model_is_refused_never_free(db):
    with pytest.raises(NoPrice):
        B(db, cap=100).call(provider="claude", model="claude-unpriced", step="x", est_input_tokens=1,
                            max_output_tokens=1, fn=ok(1, 1))
    out, fell = B(db).call_or_fallback(lambda: "fb", provider="claude", model="nope", step="x", est_input_tokens=1,
                                       max_output_tokens=1, fn=ok(1, 1))
    assert fell and out == "fb"


def test_api_keys_never_logged(db, caplog, monkeypatch):
    key = "sk-ant-api03-SECRETSECRET"
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)

    def leaky():
        raise RuntimeError(f"401 invalid x-api-key {key}")

    caplog.set_level(logging.DEBUG)
    B(db, cap=1.0).call_or_fallback(lambda: None, provider="claude", model="claude-x", step="findings",
                                    est_input_tokens=1, max_output_tokens=1, fn=leaky)
    assert key not in caplog.text
    dump = " ".join(str(v) for r in db.query("SELECT * FROM ai_spend") for v in r.values())
    assert key not in dump and "SECRET" not in dump


def test_shipped_price_table_is_dated_and_jev_priced():
    p = load_prices()
    assert p["as_of"] == "2026-10-18" and p["models"]["jev-1.13.0"]["input"] == 0.042


def test_spend_endpoint(client):
    sid = client.post("/api/studies", json={"name": "x", "mode": "profile"}).json()["id"]
    r = client.get(f"/api/studies/{sid}/spend").json()
    assert r["cap_usd"] == 1.0 and r["spent_usd"] == 0
