# California: Caltrans TASAS / TSN (state highway crashes)

**What:** Caltrans's Traffic Accident Surveillance and Analysis System, inside the Transportation System Network (TSN)
database. Caltrans coders assign each state-highway crash (from CCRS, FARS, AARS, SWITRS) to a postmile and code the
sequence of events. Basis of Caltrans HSIP work and the **average crash rates** (rate groups) Caltrans publishes.
**Access:** request form → District Traffic Safety (Caltrans projects) or CPRA (others). **Output is PDF only.** 10 complete
years + current. Annual summary book: "Crash Data on California State Highways" (2024 edition prepared 03/18/2026).
**Not a feed CrashIQ can pull.**

## 2024 statewide (Caltrans book, p.10)
All SHS: 153,588 crashes (PDO 98,919; injury 53,332; fatal 1,337; killed 1,467).
Freeways: 127,545 crashes (PDO 84,870; fatal 808; killed 882). Non-freeway: 26,043 (fatal 529).

## Versus CCRS (2026-10-18)
- Freeways: CCRS `IsFreeway` 133,289 (+4.5%); fatal crashes 946 (+17%); killed 1,049 (+19%).
- All SHS: CCRS `IsHighwayRelated` 163,317 (+6.3%); fatal 1,492 (+12%).
- Why: Caltrans counts only crashes *on* the state highway. It excludes crashes "associated with" it (CHP Collision
  Investigation Manual), suicides and beat 902 incidents. CCRS flags are the officer's and broader.
- Rule: rates compared to Caltrans averages must use Caltrans's counting rule, or say they are approximate.
