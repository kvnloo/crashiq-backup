# Shared fix proposed by the KS branch (not applied; Hermes merges centrally)

## Per-person crash costs (Kansas)
KDOT prices each injured person, not the crash (2023 Kansas Traffic Crash Facts p. 77): cost = sum over people of
K $14,029,605 / A $774,356 / B $248,477 / C $141,166, or $11,900 when nobody is hurt (2019 dollars).
`profile._cost` prices `costs[c["severity"]]` once per crash, so KS ships with `crash_costs` missing.

Fix (profile.py `_cost`, non-CA branch):

```python
if costs.get("per_person"):
    per = lambda c: (sum(costs[k] for k in c.get("person_kabco") or []) or costs["O"]) if c.get("severity") in "KABCO" else 0
    return {"crash_cost": sum(per(c) for c in cs), "cost_unpriced": sum(c.get("severity") == "U" for c in cs)}
```

The KS reader would then add `person_kabco` (one letter per K/A/B/C person, from the counts, as `va_vdot` does) and
methods_ks.json would move `person_costs` to `crash_costs` with `"per_person": true`, `"O": 11900`.

Test:

```python
def test_per_person_costs_add_up():
    costs = {"per_person": True, "K": 10, "A": 5, "B": 2, "C": 1, "O": 0.5, "dollar_year": 2019}
    cs = [{"severity": "B", "person_kabco": ["B", "B", "C"]}, {"severity": "O", "person_kabco": []}]
    assert profile._cost(pack_ks, costs, cs, None, None)["crash_cost"] == 5.5
```

The source note in `profile.build` also says "one cost per KABCO level"; it would need "per injured person" for such packs.
