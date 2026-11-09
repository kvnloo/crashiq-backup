# Shared fixes found by the Tennessee build (Hermes, 2026-11-08)

## names.street_key: read PKE as PIKE

Metro Nashville writes Pike as `PKE` ("NOLENSVILLE PKE & THOMPSON LN"); `street_key("NOLENSVILLE PKE")` gives core
`NOLENSVILLE PKE`, while OSM/TIGER "Nolensville Pike" gives `NOLENSVILLE PIKE`, so the not-on-the-corridor-street
check and name placement miss. Worked around in `tn_tdoshs.nashville_record` (PKE -> PIKE).

Fix: add `PKE` as a spelling of `PIKE` in names.py's suffix/word table.

Test:
```python
def test_pke_is_pike():
    assert names.street_key("NOLENSVILLE PKE") == names.street_key("Nolensville Pike")
```
