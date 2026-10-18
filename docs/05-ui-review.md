# CrashIQ — UI review of mockup v0.1 (2026-10-17)

Source: `design/mockups/index.html` (Claude Code mockup, Signal Flow theme). The user saw it on a tablet:
"super impressed", but asked for changes.

## User's design rules (standing)
1. **Every element has a purpose.** If it doesn't serve one, it's not on the screen.
2. **Minimal by default.** Collapse choices into dropdowns (e.g. years). The important things should pop.
3. **Nothing confusing.** Every button says plainly what it does.
4. Change the branding in the top-right corner (pending user's direction, see Q-UI1).

## Element inventory: purpose → proposal
Legend: KEEP · CUT · CHANGE · HIDE (behind "More options" / shown only when relevant)

**Header**
| Element | What it does now | Proposal |
|---|---|---|
| Animated signal lamp + "CrashIQ" (left) | Logo; animation is decorative | CHANGE: static logo; final name pending (name conflict) |
| Project name "Crenshaw Blvd · Marine → 132nd" | Shows the current study | KEEP |
| "Example data" badge (right) | Mockup disclaimer | CUT in the app; show a warning only when data is preliminary |
| ◐ button (right) | Toggles light/dark theme | CUT, pick one theme; or move into an account menu |

**Left rail**
| Steps 1–6 with subtitles | Navigation + progress | KEEP, but **5 steps** (user, 2026-10-18): Setup · Corridor (draw + review together) · Crash profile · Findings · Export; drop subtitles once the step titles are clear |
| Footer "Mockup v0.1 · Data: CCRS · Map ©" | Credits | KEEP the data/map credit (required, small); CUT "Mockup v0.1" |

**1 Setup**
| Animated road / signal hero | Decoration | ~~CUT~~ **KEEP** (user, 2026-10-18: "I really like the traffic"); headline above it, never on top of it |
| Study type cards (5; 3 say "Coming v2") | Choose the study mode | CHANGE: one dropdown with only the 2 working modes; no "coming soon" items |
| Project name | Names the study | KEEP |
| Year chips (one per year) | Choose crash history window | CHANGE: dropdown "Last 5 complete years (2021–2025) ▾" with a "Custom range" option |
| "Draw the corridor →" | Next step | KEEP |

**2 Study area**
| "✎ Corridor" tool | The only drawing tool (always on) | CUT: drawing is the default, no button needed |
| "◎ Intersections only" (disabled, v2) | Nothing yet | CUT |
| "↺ Redraw" | Clears the line | KEEP, rename "Clear line" |
| Back / "Review locations →" | Navigation | KEEP |

**3 Review locations**
| Influence radius slider (250 ft) | Changes intersection assignment | HIDE under "More options" (default 250 ft per HSM/Caltrans) |
| "+ Enter AADT to compute rates" | Turns on crash rates | HIDE under "More options" |
| Back / "Build the profile →" | Navigation | KEEP |

**4 Crash profile**
| KPI strip | Headline numbers | KEEP (max 4 KPIs) |
| Map columns + severity legend | Where crashes are | KEEP |
| Collision type bars, Hour × Day heatmap, Locations table | The profile | KEEP |
| "table T2 · computed" labels | Provenance | CHANGE: small ⓘ icon with tooltip, not visible text |
| Back / "See findings →" | Navigation | KEEP |

**5 Findings**
| Finding list | One card per pattern | KEEP |
| Crash animation + "❚❚ Pause" / "↺ Replay" + phases | Animated schematic of the crash pattern | CHANGE: static diagram by default; play on tap; cut Pause/Replay buttons |
| Tabs: Records / Collision diagram / Audit | Evidence behind the finding | KEEP (this is the trust feature) |
| Accept / Edit / Reject | Approve findings | KEEP |
| "Ask about this corridor — query tools only" + Ask | Follow-up questions | KEEP; CUT "query tools only" (jargon) |

**6 Export**
| PDF / Excel checkboxes | Choose outputs | KEEP |
| "Include rejected findings" | Appendix option | HIDE under "More options" |
| Page previews | Shows what you'll get | KEEP |
| "Export 2 files ↓" | Download | KEEP |

## Count
About 12 elements cut or hidden, 6 changed. Every remaining control is navigation, an input the study needs,
or evidence for a finding.

## Open
- **Q-UI1:** top-right branding: what should change (name, logo, colors, or remove the badge/theme button)?
- **Q-UI2 DECIDED (2026-10-17):** keep "CrashIQ" for now; revisit the name before paid launch (name conflict noted).
- **Note:** `design/mockups/` is not committed to git yet (it lives only on the Mac).
