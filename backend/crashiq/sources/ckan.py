"""Minimal CKAN action-API client (data.ca.gov). One injectable `transport` so tests and the offline demo
never touch the network."""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

API = "https://data.ca.gov/api/3/action/"

# transport(action, params) -> the action's `result` object. Raise on failure.
Transport = Callable[[str, dict], dict]


class CkanError(RuntimeError):
    """data.ca.gov failed after retries. Never turned into an empty crash list."""


def http_transport(action: str, params: dict, timeout: float = 120) -> dict:
    url = API + action + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "CrashIQ/0.1 (+crash safety analysis)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.load(r)
    if not body.get("success"):
        raise CkanError(f"CKAN {action} error: {body.get('error')}")
    return body["result"]


def _error_body(e: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(e.read().decode("utf-8", "replace"))
        err = body.get("error") or {}
        return str(err.get("message") or err.get("info") or err)[:300]
    except Exception:  # noqa: BLE001 - best effort; the status code alone is still reported
        return "no detail"


META_TTL_S = 24 * 3600
_META_CACHE: dict[tuple, tuple[float, dict]] = {}


class Ckan:
    def __init__(self, transport: Transport | None = None, retries: int = 3, backoff_s: float = 3.0,
                 sleep: Callable[[float], None] = time.sleep):
        self.transport = transport or http_transport
        self.retries, self.backoff_s, self.sleep = retries, backoff_s, sleep
        self.calls = 0

    def get(self, action: str, **params) -> dict:
        # Live data.ca.gov only: the resource list and column lists change about once a year, but every pull
        # asked for all of them again (15 calls). Kept for a day per process (#54). SQL is never cached here.
        live = self.transport is http_transport and action in ("package_show", "datastore_search")
        key = (action, tuple(sorted(params.items())))
        if live:
            hit = _META_CACHE.get(key)
            if hit and time.time() - hit[0] < META_TTL_S:
                return hit[1]
        res = self._get(action, **params)
        if live:
            _META_CACHE[key] = (time.time(), res)
        return res

    def _get(self, action: str, **params) -> dict:
        last = "no response"
        for attempt in range(self.retries + 1):
            try:
                self.calls += 1
                return self.transport(action, params)
            except urllib.error.HTTPError as e:      # data.ca.gov returns 502/504 under load
                last = f"HTTP {e.code}"
                if e.code not in (429, 500, 502, 503, 504):
                    last += f" ({_error_body(e)})"     # 400/409 carry the real SQL error; keep it
                    break
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as e:
                last = str(e) or type(e).__name__
            except ValueError:                        # an HTML error page instead of JSON
                last = "a response that wasn't JSON"
            if attempt < self.retries:
                self.sleep(self.backoff_s * 2 ** attempt)
        raise CkanError(f"Couldn't get crash data from data.ca.gov: {last}. Try again in a few minutes.")

    def sql_page(self, sql: str) -> tuple[list[dict], bool]:
        """(records, truncated) — for callers that page and can shrink the page when the server caps rows."""
        res = self.get("datastore_search_sql", sql=sql)
        return res["records"], bool(res.get("records_truncated"))

    def sql(self, sql: str) -> list[dict]:
        res = self.get("datastore_search_sql", sql=sql)
        if res.get("records_truncated"):
            # data.ca.gov caps rows per query; a capped answer must never pass as the whole answer
            raise CkanError(f"data.ca.gov returned only part of a result ({len(res['records'])} rows; server row "
                            "limit). The pull was stopped so crashes aren't silently missing.")
        return res["records"]

    def fields(self, resource_id: str) -> list[dict]:
        """[{id, type}] for a datastore resource (column names exactly as stored)."""
        return [f for f in self.get("datastore_search", resource_id=resource_id, limit=0)["fields"]
                if not f["id"].startswith("_")]
