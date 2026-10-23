# Street alias table: DRAFT for your review (#230)

Measure and draft only: the app doesn't read this file. Every entry needs your yes before it is used (CLAUDE.md). Basis: CCRS mirror 2026-10-19, OSM 2026-10-18, run-8 street maps (city box + 1 km), app code main. Scope: one city each (aliases are local).

## How an entry is proposed
- A report name that matches no street on the city's map, in crashes whose other street is on the map.
- Evidence it is map street M: in at least 3 crashes, the other street meets exactly one street that resembles the name (similarity >= 0.75, clearly ahead of the next), and at least 80% of those crashes point to the same M; no second street with 20% (or 2 crashes) of them.
- Check on hidden police GPS: the crashes with that name whose GPS agrees with the report (once the alias is read) are placed with the alias and the GPS hidden; an entry is dropped if fewer than 90% land at the right intersection. The GPS never chose M, so this is a held-out check.

## Summary

- **912 entries proposed**, which would place **4,635 difficult crashes** with the app's current gate. On hidden GPS they are right at the intersection 3,724 of 3,792 times (98.2%, 95% low 97.7%).
- By kind: 161 entries (2,287 crashes) are standard abbreviations spelled out (JR = Junior, EXPWY = Expressway, RT = Route, PW = Parkway, TRL = Trail, HW = Highway): one name-cleaner rule would fix them in every city, so they are better approved as rules than as entries. 751 entries (2,348 crashes) are local spellings or names (HAWTHORN BL = Hawthorne Boulevard, FAIRMONT AV = Fairmount Avenue): the real alias table.
- 465 of the 912 entries (2,850 crashes) have no crash with GPS to check them: they rest on the street evidence alone (marked "no GPS to check"); the rest are checked as above.
- 12,762 candidates excluded: only N crashes point to one street 12,588; hidden GPS right only N/N 630; ambiguous 42; agreement N% 26; route number mismatch 16.
- The long tail: 11,689 candidates rest on a single crash (one-off misspellings such as MAONOLIA, HYPE PARK DR). A table can't cover them; the fuzzy tier holds them for review today.
- 139 candidates are one pattern, a route number after the name ("PACIFIC COAST HWY - SR1", "BEACH BL - SR39") or a direction in brackets ("(N)"): better fixed once in the name cleaner (a rule, like #212) than city by city.

## Top entries by crashes they would place

| # | City | Report says | Map street | Kind | Crashes pointing to it | Difficult crashes with the name | Would place | Hidden GPS right | Example crash ids |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Oakland | MARTIN LUTHER KING JR WY | Martin Luther King Junior Way | abbreviation | 392 (100.0%) | 404 | 390 | no GPS to check | 2728463 2738440 2732967 |
| 2 | Rancho Cucamonga | ARROW RT | Arrow Route | abbreviation | 209 (100.0%) | 269 | 260 | 6/6 | 2731990 2802397 2810312 |
| 3 | San Jose | E CAPITOL EXPWY | East Capitol Expressway | abbreviation | 226 (100.0%) | 176 | 166 | 10/11 | 2731048 2728553 2727181 |
| 4 | Merced | MARTIN LUTHER KING JR WY | Martin Luther King Junior Way | abbreviation | 124 (100.0%) | 125 | 124 | no GPS to check | 1553833 2731664 2737632 |
| 5 | Rancho Cucamonga | ARROW RTE | Arrow Route | abbreviation | 112 (100.0%) | 112 | 106 | 2/2 | 2737633 2731998 2731991 |
| 6 | Ontario | ONTARIO MILLS PW | Ontario Mills Parkway | abbreviation | 46 (100.0%) | 73 | 69 | no GPS to check | 1401292 1417348 1414054 |
| 7 | Napa | SILVERADO TRL | Silverado Trail | abbreviation | 101 (100.0%) | 67 | 64 | 30/30 | 2728090 2739087 2732125 |
| 8 | San Jose | SAN TOMAS EXPWY | San Tomas Expressway | abbreviation | 69 (100.0%) | 57 | 56 | no GPS to check | 2728532 2726953 2746497 |
| 9 | Sacramento | MARTIN LUTHER KING JR BL | Martin Luther King Junior Boulevard | abbreviation | 59 (100.0%) | 56 | 56 | no GPS to check | 2730656 2726580 2735326 |
| 10 | Laguna Niguel | PASEO DE COLINAS | Paseo de la Colinas | local spelling or name | 53 (100.0%) | 53 | 53 | no GPS to check | 2728482 2751877 2742570 |
| 11 | Long Beach | MARTIN LUTHER KING JR AV | Martin Luther King Junior Avenue | abbreviation | 73 (100.0%) | 52 | 51 | 55/59 | 2783188 2814988 2854533 |
| 12 | Los Altos | FOOTHILL EXPWY | Foothill Expressway | abbreviation | 45 (100.0%) | 53 | 48 | 5/5 | 2740067 2739885 2767654 |
| 13 | San Jose | MONTAGUE EXPWY | Montague Expressway | abbreviation | 48 (100.0%) | 43 | 40 | no GPS to check | 2732362 2768989 2767871 |
| 14 | Windsor | OLD REDWOOD HW | Old Redwood Highway | abbreviation | 79 (100.0%) | 42 | 36 | 37/40 | 1869467 1869466 1869460 |
| 15 | Torrance | HAWTHORN BL | Hawthorne Boulevard | local spelling or name | 28 (100.0%) | 36 | 36 | 1/1 | 2732846 2750749 2746512 |
| 16 | Huntington Beach | PACIFIC COAST HWY - SR1 | Pacific Coast Highway | local spelling or name | 476 (100.0%) | 64 | 34 | 225/244 | 1381453 1403695 1403694 |
| 17 | Encinitas | N COAST HWY 101 | North Coast Highway 101 | abbreviation | 34 (100.0%) | 34 | 33 | no GPS to check | 2753534 2874474 2874201 |
| 18 | Dublin | VILLAGE PW | Village Parkway | abbreviation | 77 (100.0%) | 31 | 31 | 40/40 | 2773626 2782575 2782574 |
| 19 | Los Angeles | W MARTIN LUTHER KING JR BL | West Martin Luther King Junior Boulevard | abbreviation | 27 (100.0%) | 30 | 30 | no GPS to check | 1488218 2731861 2731381 |
| 20 | Campbell | SAN TOMAS EXPWY | San Tomas Expressway | abbreviation | 18 (100.0%) | 41 | 29 | no GPS to check | 2798716 2806387 2844530 |
| 21 | Desert Hot Springs | TWO BUNCH PALMS TRL | Two Bunch Palms Trail | abbreviation | 84 (100.0%) | 29 | 29 | 54/55 | 1417602 1426556 1470654 |
| 22 | San Jose | W CAPITOL EX | West Capitol Expressway | abbreviation | 38 (100.0%) | 30 | 27 | no GPS to check | 2747672 2781516 2806302 |
| 23 | Oceanside | VANDERGRIFT BL | Vandegrift Boulevard | local spelling or name | 24 (100.0%) | 30 | 27 | no GPS to check | 2739065 2736044 2807782 |
| 24 | San Diego | FAIRMONT AV | Fairmount Avenue | local spelling or name | 28 (100.0%) | 37 | 27 | no GPS to check | 2758669 2780378 2778118 |
| 25 | Sacramento | SUMMERSDALE DR | Summerdale Way | local spelling or name | 27 (100.0%) | 26 | 26 | no GPS to check | 2733917 2755423 2812063 |
| 26 | San Jose | SOUTHWEST EXPWY | Southwest Expressway | abbreviation | 19 (100.0%) | 26 | 25 | no GPS to check | 2761068 2832485 2607962 |
| 27 | Antioch | CANADA VALLEY RD | Cañada Valley Road | local spelling or name | 27 (100.0%) | 25 | 25 | 1/1 | 1721231 2788157 2798912 |
| 28 | Los Angeles | LAUREL CYN BL | Laurel Canyon Boulevard | abbreviation | 24 (100.0%) | 25 | 24 | no GPS to check | 2731527 2728994 2740660 |
| 29 | Berkeley | MARTIN LUTHER KING JR | Martin Luther King Junior Way | local spelling or name | 146 (100.0%) | 28 | 23 | 102/107 | 2741852 2755607 2755399 |
| 30 | Menifee | SH-74 | CA 74 | local spelling or name | 61 (100.0%) | 23 | 23 | 38/38 | 1931160 1860552 1871757 |
| 31 | Downey | STEWART | Stewart and Gray Road | local spelling or name | 22 (100.0%) | 22 | 22 | no GPS to check | 2866126 2606593 2647632 |
| 32 | San Jose | LAWRENCE EXPWY | Lawrence Expressway | abbreviation | 24 (100.0%) | 26 | 21 | no GPS to check | 2742940 2845958 2859881 |
| 33 | Oakland | MARTIN LUTHER KING WY | Martin Luther King Junior Way | local spelling or name | 22 (100.0%) | 22 | 21 | no GPS to check | 2756598 2805845 2805089 |
| 34 | Marina | IMJIN PW | Imjin Parkway | abbreviation | 33 (100.0%) | 40 | 21 | no GPS to check | 2737921 2737206 2748127 |
| 35 | Lake Elsinore | SH 74 | CA 74 | local spelling or name | 87 (100.0%) | 29 | 19 | 41/41 | 1414822 1424760 1467481 |
| 36 | San Juan Capistrano | AVE DE LA VISTA | Avenida de la Vista | local spelling or name | 19 (100.0%) | 19 | 19 | no GPS to check | 2738022 2791391 2817298 |
| 37 | Soledad | DIXIE ST | Dixi Street | local spelling or name | 19 (100.0%) | 20 | 19 | no GPS to check | 2779690 2779599 2805980 |
| 38 | Corona | EAGLE GLEN PY | Eagle Glen Parkway | abbreviation | 43 (100.0%) | 18 | 18 | 18/19 | 1391141 1421873 1433835 |
| 39 | Tulare | MARTIN LUTHER KING | Martin Luther King Junior Avenue | local spelling or name | 19 (100.0%) | 18 | 18 | 5/5 | 2759713 2758846 2767464 |
| 40 | Laguna Hills | MOULTON PKY | Moulton Parkway | local spelling or name | 19 (100.0%) | 18 | 18 | 1/1 | 2817492 2856176 2614715 |

All 912 entries: data/reference/street_aliases_DRAFT.csv (status `proposed`). Excluded candidates with their reason: data/statewide/alias_excluded.csv.
