# Difficult bin, Part A (current main e2f1633 (backend unchanged since): #199 file re-placed with bin2.py, CCRS mirror 2026-10-19)

285,580 of 2,057,508 CCRS crashes 2021-2025 (13.9%).

| Reason | Crashes | Share of bin | Police GPS present but off the roads |
|---|---|---|---|
| unique pair held by the gate (#201: the two streets meet only once) | 106,707 | 37.4% | 4,190 |
| relaxed match held by the gate | 9,977 | 3.5% | 466 |
| named streets don't meet on the map | 111,475 | 39.0% | 44,005 |
| no cross street (blank, NOT STATED, UNKNOWN, PRIVATE PROPERTY) | 25,114 | 8.8% | 1,962 |
| near / fuzzy match held by the gate | 21,715 | 7.6% | 6,348 |
| streets meet in more than one place | 6,738 | 2.4% | 1,056 |
| no street map for this place | 3,854 | 1.3% | 3,068 |

## Caltrans district

| Caltrans district | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| District 1 | 1,099 | 228 | 34 | 577 | 50 | 56 | 53 | 101 | 592 |
| District 2 | 2,250 | 155 | 67 | 1,536 | 48 | 123 | 71 | 250 | 1,030 |
| District 3 | 13,464 | 465 | 316 | 8,204 | 1,455 | 1,756 | 778 | 490 | 5,789 |
| District 4 | 35,757 | 4,523 | 1,580 | 20,914 | 2,594 | 4,667 | 1,217 | 262 | 11,205 |
| District 5 | 9,518 | 2,535 | 417 | 4,156 | 673 | 633 | 241 | 863 | 2,142 |
| District 6 | 19,257 | 8,499 | 760 | 6,531 | 1,434 | 677 | 256 | 1,100 | 5,622 |
| District 7 | 108,163 | 63,065 | 3,533 | 31,390 | 3,208 | 5,215 | 1,594 | 158 | 15,625 |
| District 8 | 37,862 | 9,928 | 1,294 | 15,989 | 6,696 | 2,931 | 884 | 140 | 8,261 |
| District 9 | 196 | 20 | 0 | 136 | 1 | 0 | 15 | 24 | 163 |
| District 10 | 10,317 | 3,174 | 332 | 3,407 | 2,226 | 718 | 264 | 196 | 2,782 |
| District 11 | 21,159 | 4,313 | 953 | 10,596 | 1,559 | 2,691 | 842 | 205 | 3,736 |
| District 12 | 26,493 | 9,802 | 691 | 8,039 | 5,168 | 2,248 | 523 | 22 | 4,146 |
| unknown | 45 | 0 | 0 | 0 | 2 | 0 | 0 | 43 | 2 |

## Road type

| Road type | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| city street | 224,398 | 105,735 | 9,706 | 68,402 | 23,616 | 11,604 | 5,335 | 0 | 18,377 |
| freeway | 31,521 | 42 | 14 | 24,579 | 665 | 5,826 | 285 | 110 | 30,266 |
| state highway (off freeway) | 19,177 | 927 | 156 | 12,249 | 556 | 4,218 | 776 | 295 | 4,698 |
| county road (outside cities) | 10,484 | 3 | 101 | 6,245 | 277 | 67 | 342 | 3,449 | 7,754 |

## Severity

| Severity | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| fatal | 936 | 278 | 23 | 495 | 33 | 35 | 17 | 55 | 339 |
| serious injury (KSI, not fatal) | 12,327 | 5,586 | 432 | 4,456 | 362 | 766 | 297 | 428 | 2,534 |
| other | 272,317 | 100,843 | 9,522 | 106,524 | 24,719 | 20,914 | 6,424 | 3,371 | 58,222 |

## Top 25 cities (CCRS city name)

| Top 25 cities (CCRS city name) | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| Los Angeles | 41,204 | 29,670 | 1,288 | 7,649 | 202 | 1,730 | 665 | 0 | 2,771 |
| Unincorporated | 12,663 | 2 | 102 | 7,796 | 375 | 1,168 | 616 | 2,604 | 11,908 |
| Long Beach | 9,554 | 6,385 | 192 | 2,516 | 23 | 384 | 54 | 0 | 651 |
| San Diego | 9,186 | 1,370 | 297 | 5,502 | 345 | 1,366 | 306 | 0 | 1,824 |
| Sacramento | 6,299 | 71 | 75 | 4,215 | 709 | 869 | 360 | 0 | 2,321 |
| Lancaster | 5,763 | 3,641 | 38 | 1,766 | 92 | 129 | 97 | 0 | 209 |
| Ontario | 5,323 | 3,781 | 35 | 740 | 435 | 283 | 49 | 0 | 279 |
| Anaheim | 5,122 | 3,701 | 28 | 876 | 204 | 283 | 30 | 0 | 655 |
| San Jose | 4,618 | 775 | 143 | 3,042 | 10 | 554 | 94 | 0 | 1,087 |
| Pasadena | 4,402 | 3,565 | 173 | 560 | 6 | 65 | 33 | 0 | 123 |
| Riverside | 3,996 | 141 | 42 | 1,817 | 1,753 | 168 | 75 | 0 | 1,162 |
| Fresno | 3,513 | 766 | 35 | 1,551 | 1,037 | 93 | 31 | 0 | 827 |
| Oakland | 3,498 | 344 | 371 | 1,544 | 30 | 1,049 | 160 | 0 | 743 |
| Santa Ana | 3,116 | 144 | 67 | 443 | 2,290 | 161 | 11 | 0 | 404 |
| Madera | 2,997 | 1,833 | 267 | 721 | 88 | 70 | 18 | 0 | 187 |
| Fullerton | 2,969 | 2,277 | 10 | 470 | 55 | 129 | 28 | 0 | 343 |
| Glendale | 2,888 | 2,035 | 110 | 395 | 276 | 54 | 18 | 0 | 110 |
| Tulare | 2,663 | 2,225 | 39 | 220 | 72 | 35 | 72 | 0 | 101 |
| San Francisco | 2,618 | 23 | 295 | 1,880 | 10 | 361 | 49 | 0 | 182 |
| Ventura | 2,554 | 1,597 | 117 | 706 | 3 | 103 | 28 | 0 | 336 |
| Stockton | 2,358 | 127 | 11 | 487 | 1,673 | 54 | 6 | 0 | 487 |
| Corona | 2,187 | 606 | 34 | 834 | 507 | 133 | 73 | 0 | 696 |
| La Habra | 2,096 | 1,778 | 42 | 258 | 0 | 11 | 7 | 0 | 2 |
| Oceanside | 2,078 | 664 | 188 | 873 | 15 | 240 | 98 | 0 | 73 |
| San Bernardino | 2,057 | 918 | 65 | 825 | 117 | 95 | 37 | 0 | 555 |

## Top 25 agencies (NCIC)

| Top 25 agencies (NCIC) | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| 1942 Los Angeles + 18 more city names (local) | 38,548 | 29,634 | 1,287 | 5,714 | 178 | 1,076 | 659 | 0 | 84 |
| 1900 Lancaster + 48 more city names (local) | 16,264 | 7,031 | 721 | 6,491 | 530 | 1,140 | 343 | 8 | 2,193 |
| 1941 Long Beach (local) | 9,262 | 6,382 | 191 | 2,336 | 23 | 280 | 50 | 0 | 376 |
| 3711 San Diego (local) | 7,282 | 1,370 | 296 | 4,110 | 148 | 1,058 | 300 | 0 | 28 |
| 3300 Moreno Valley + 29 more city names (local) | 5,969 | 253 | 103 | 2,367 | 2,931 | 223 | 91 | 1 | 715 |
| 3607 Ontario + 3 more city names (local) | 5,031 | 3,783 | 35 | 528 | 435 | 201 | 49 | 0 | 3 |
| 3001 Anaheim + 4 more city names (local) | 4,590 | 3,703 | 28 | 508 | 197 | 128 | 26 | 0 | 140 |
| 3600 Victorville + 13 more city names (local) | 4,530 | 166 | 553 | 2,673 | 154 | 756 | 228 | 0 | 367 |
| 1953 Pasadena (local) | 4,292 | 3,562 | 172 | 462 | 5 | 58 | 33 | 0 | 3 |
| 3404 Sacramento + 3 more city names (local) | 3,979 | 70 | 75 | 2,230 | 592 | 652 | 360 | 0 | 15 |
| 4313 San Jose (local) | 3,821 | 771 | 144 | 2,384 | 8 | 426 | 88 | 0 | 299 |
| 3313 Riverside (local) | 2,943 | 141 | 41 | 829 | 1,738 | 124 | 70 | 0 | 142 |
| 1005 Fresno (local) | 2,908 | 761 | 35 | 972 | 1,033 | 76 | 31 | 0 | 222 |
| 2002 Madera (local) | 2,812 | 1,833 | 267 | 537 | 89 | 69 | 17 | 0 | 0 |
| 1925 Glendale + 3 more city names (local) | 2,806 | 2,035 | 111 | 319 | 277 | 46 | 18 | 0 | 24 |
| 3019 Santa Ana + 6 more city names (local) | 2,773 | 143 | 67 | 250 | 2,285 | 22 | 6 | 0 | 67 |
| 0109 Oakland (local) | 2,744 | 344 | 370 | 1,068 | 27 | 780 | 155 | 0 | 5 |
| 3008 Fullerton (local) | 2,646 | 2,276 | 10 | 236 | 45 | 51 | 28 | 0 | 26 |
| 5406 Tulare (local) | 2,619 | 2,225 | 39 | 177 | 74 | 32 | 72 | 0 | 57 |
| 9550 Unincorporated + 53 more city names (CHP) | 2,564 | 0 | 2 | 2,205 | 51 | 292 | 7 | 7 | 2,521 |
| 3801 San Francisco (local) | 2,452 | 22 | 294 | 1,731 | 8 | 338 | 48 | 11 | 14 |
| 3700 Vista + 9 more city names (local) | 2,436 | 586 | 150 | 995 | 34 | 519 | 152 | 0 | 28 |
| 5600 Thousand Oaks + 7 more city names (local) | 2,411 | 1,193 | 38 | 802 | 210 | 77 | 91 | 0 | 1,137 |
| 3000 Mission Viejo + 13 more city names (local) | 2,390 | 296 | 168 | 1,186 | 0 | 550 | 190 | 0 | 47 |
| 5608 Ventura (local) | 2,285 | 1,592 | 109 | 454 | 2 | 100 | 28 | 0 | 70 |
