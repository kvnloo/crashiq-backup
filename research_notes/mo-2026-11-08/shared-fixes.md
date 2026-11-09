# Shared fixes found by the Missouri build (Hermes, 2026-11-08)

None needed. MSHP's road prefixes (CST/CRD/PVT, `IS 70`) are rewritten inside `mo_mshp.road` (`DALE AVE`, `I 70`);
`MO 78` is already read as a state route by names.py (STATE_ROUTE_PREFIXES has MO). Candidate, not required: teach
names.py MUCR's `IS n` = `I n` if another Missouri source appears.
