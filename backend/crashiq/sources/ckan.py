"""Minimal CKAN action-API client (data.ca.gov). One injectable `transport` so tests and the offline demo
never touch the network."""

from __future__ import annotations

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


class Ckan:
    def __init__(self, transport: Transport | None = None, retries: int = 3, backoff_s: float = 3.0,
                 sleep: Callable[[float], None] = time.sleep):
        self.transport = transport or http_transport
        self.retries, self.backoff_s, self.sleep = retries, backoff_s, sleep
        self.calls = 0

    def get(self, action: str, **params) -> dict:
        last = "no response"
        for attempt in range(self.retries + 1):
            try:
                self.calls += 1
                return self.transport(action, params)
            except urllib.error.HTTPError as e:      # data.ca.gov returns 502/504 under load
                last = f"HTTP {e.code}"
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = str(e) or type(e).__name__
            if attempt < self.retries:
                self.sleep(self.backoff_s * 2 ** attempt)
        raise CkanError(f"Couldn't get crash data from data.ca.gov: {last}. Try again in a few minutes.")

    def sql(self, sql: str) -> list[dict]:
        return self.get("datastore_search_sql", sql=sql)["records"]

    def fields(self, resource_id: str) -> list[dict]:
        """[{id, type}] for a datastore resource (column names exactly as stored)."""
        return [f for f in self.get("datastore_search", resource_id=resource_id, limit=0)["fields"]
                if not f["id"].startswith("_")]
