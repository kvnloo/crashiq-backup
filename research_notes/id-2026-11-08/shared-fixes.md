# Shared fixes Idaho would use (not made on this branch)

## 1. A source's last full year, not only a lag in months
ITD's open service runs about three years behind (on 2026-11-08: 2022 in full, 2023 to 2023-10-01, nothing later).
`StatePack.final_lag_months` can only express that as a fixed lag (46 here), which drifts if ITD catches up or falls
further behind. The reader already knows the truth (`id_itd.last_full_year`, one statistics query).
Fix: an optional `StatePack.last_year: Callable[[], int] | None` that `study.last_final_year` takes as an upper bound
(cached per day). Test: with `last_year=lambda: 2022` and today 2027-06-01, `default_window` is (2018, 2022).
Until then the reader reports part years as `years_missing` and drops their rows, so nothing is miscounted.

## 2. `study.default_window` doesn't clamp to `pack.first_year`
Same as Arkansas's shared-fixes #4; not hit by Idaho (first_year 2008).
