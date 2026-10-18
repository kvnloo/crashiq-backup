"""C15 budget: every Claude and Jev call goes through `Budget.call`, which enforces a per-study USD cap in code
and logs tokens and dollars. Analysis never blocks on AI: when a call is refused or fails, `call_or_fallback`
returns the step's fallback (docs/04-design.md §4 #8):
  - Jev J1 leftovers → review queue
  - Claude analyst   → profile + tables, no narrative

Prices: config/prices.json (dated). A model without a price is refused, never treated as free.
Logged per call: study, provider, model, step, tokens, USD, outcome. Never prompts, responses or keys.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Request

from . import study as study_mod
from .db import Database

PRICES_PATH = Path(__file__).parent / "config" / "prices.json"
log = logging.getLogger("crashiq.budget")


class BudgetExceeded(RuntimeError):
    pass


class NoPrice(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0


def load_prices(path: Path = PRICES_PATH) -> dict:
    return json.loads(path.read_text())


class Budget:
    def __init__(self, db: Database, study_id: str, cap_usd: float, prices: dict | None = None):
        self.db, self.study_id, self.cap_usd = db, study_id, float(cap_usd)
        self.prices = (prices or load_prices())["models"]

    # -- money ----------------------------------------------------------------------------------------
    def _price(self, model: str) -> dict:
        p = self.prices.get(model)
        if not p or p.get("input") is None or p.get("output") is None:
            raise NoPrice(f"No price on file for {model}; the call is refused until config/prices.json has one.")
        return p

    def cost(self, model: str, usage: Usage) -> float:
        p = self._price(model)
        fresh_in = max(0, usage.input_tokens - usage.cache_read_tokens)
        cache = usage.cache_read_tokens * (p.get("cache_read") if p.get("cache_read") is not None else p["input"])
        return (fresh_in * p["input"] + usage.output_tokens * p["output"] + cache) / 1e6

    def spent(self) -> float:
        r = self.db.one("SELECT COALESCE(SUM(usd), 0) AS s FROM ai_spend WHERE study_id = ?", (self.study_id,))
        return float(r["s"])

    def remaining(self) -> float:
        return max(0.0, self.cap_usd - self.spent())

    # -- calls ----------------------------------------------------------------------------------------
    def call(self, *, provider: str, model: str, step: str, est_input_tokens: int, max_output_tokens: int,
             fn: Callable[[], tuple[Any, Usage]]) -> Any:
        """Run fn() only if its worst-case cost fits under the cap; log actual usage. fn returns (result, Usage)."""
        estimate = self.cost(model, Usage(est_input_tokens, max_output_tokens))
        if self.spent() + estimate > self.cap_usd + 1e-12:
            self._log(provider, model, step, Usage(), 0.0, "refused_over_cap", estimate)
            raise BudgetExceeded(f"{step}: would exceed this study's AI cap of ${self.cap_usd:.2f} "
                                 f"(spent ${self.spent():.4f}, this call up to ${estimate:.4f}).")
        try:
            result, usage = fn()
        except Exception:
            self._log(provider, model, step, Usage(), 0.0, "error", estimate)
            raise
        usd = self.cost(model, usage)
        self._log(provider, model, step, usage, usd, "ok", estimate)
        return result

    def call_or_fallback(self, fallback: Callable[[], Any], **kw) -> tuple[Any, bool]:
        """(result, used_fallback). Over the cap, no price, or a provider error → the fallback; never blocks."""
        try:
            return self.call(**kw), False
        except (BudgetExceeded, NoPrice) as e:
            self._log(kw["provider"], kw["model"], kw["step"], Usage(), 0.0, "fallback", 0.0)
            log.info("AI fallback for study %s step %s: %s", self.study_id, kw["step"], type(e).__name__)
            return fallback(), True
        except Exception as e:  # provider/network error: same fallback, logged without the message (may echo inputs)
            self._log(kw["provider"], kw["model"], kw["step"], Usage(), 0.0, "fallback", 0.0)
            log.info("AI fallback for study %s step %s after %s", self.study_id, kw["step"], type(e).__name__)
            return fallback(), True

    def _log(self, provider, model, step, usage: Usage, usd: float, outcome: str, estimate: float) -> None:
        self.db.execute(
            "INSERT INTO ai_spend (study_id, provider, model, step, input_tokens, output_tokens, cache_read_tokens, "
            "usd, estimate_usd, outcome) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (self.study_id, provider, model, step, usage.input_tokens, usage.output_tokens, usage.cache_read_tokens,
             round(usd, 8), round(estimate, 8), outcome))
        log.info("ai_spend study=%s provider=%s model=%s step=%s in=%d out=%d usd=%.6f outcome=%s",
                 self.study_id, provider, model, step, usage.input_tokens, usage.output_tokens, usd, outcome)

    def report(self) -> dict:
        rows = self.db.query(
            "SELECT provider, model, step, outcome, COUNT(*) AS calls, SUM(input_tokens) AS input_tokens, "
            "SUM(output_tokens) AS output_tokens, SUM(usd) AS usd FROM ai_spend WHERE study_id = ? "
            "GROUP BY provider, model, step, outcome ORDER BY provider, step", (self.study_id,))
        return {"cap_usd": self.cap_usd, "spent_usd": round(self.spent(), 6), "remaining_usd": round(self.remaining(), 6),
                "by_step": rows}


router = APIRouter()


@router.get("/studies/{sid}/spend")
def get_spend(sid: str, request: Request) -> dict:
    db = request.app.state.db
    study_mod.require(db, sid)
    return Budget(db, sid, request.app.state.settings.study_ai_cap_usd).report()
