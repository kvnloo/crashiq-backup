# Shared fixes Utah would use (not made on this branch)

## 1. Utah grid street names
Utah streets are numbered on a grid: "700 South", "2100 S", "1300 E", "W 400 S", and house addresses look like
"6844 S HIGHLAND DR" or "7500 S 700 E". On State Street the corridor check worked (22 crashes on side streets were
excluded, none on State Street), but how `names.street_key` keys "2100 South" against TIGER's "2100 S" wasn't
measured. Test to add: `street_key("2100 South") == street_key("2100 S")` and `street_key("W 400 S") ==
street_key("400 South")`. Not hit by the end-to-end check (placement is by GPS).

## 2. Freeway names with direction in brackets
UDOT writes "I-15 (Northbound)", "I-215 (Westbound)" and sometimes "1-15". The freeway rules excluded the I-80 crashes
on State Street by GPS and road class, so nothing broke; a name-based freeway check would need these forms.

## 3. `study.default_window` doesn't clamp to `pack.first_year`
Same as Arkansas's and Idaho's shared-fixes; not hit by Utah (first_year 2019).
