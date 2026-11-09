# Shared fixes found by the Ohio build (not applied; for Hermes to merge centrally)

1. **Partial dates.** Ohio's public layer has year + month + weekday + hour, never the day. The reader sets
   `date = ""` and adds `month`. Shared code that would read a month if it were in the contract:
   - `profile.py` month charts
   - `review.py` news-search text (it uses `date.fromisoformat`; `"2024-08"` would raise)
   - exports' Date column

   Fix: accept `date` as `YYYY-MM` in the contract, and guard `review.py` with
   `len(c["date"]) == 10`.
   Test: `review` builds links for `{"date": "2024-08"}` without raising, and an export prints "2024-08".
2. **Route as a street name for the not-on-street check.** The NLFID gives `I-70` / `US 23` / `SR 161` on 38% of
   crashes. It's kept in `road_number`, not `primary_road`, because a crash at an intersection is coded to one route
   only, and putting it in `primary_road` would exclude crashes coded to the crossing state route. A shared
   "single-road source" mode would fix this: use the road only to drop crashes on a *grade-separated* crossing road
   (`is_freeway` already does this for FC 1-2).
   Test: a crash with `road_number="SR 315"`, `is_freeway=True` on a High St corridor is excluded; one with
   `road_number="SR 161"`, `is_freeway=False` at a study intersection is kept.
