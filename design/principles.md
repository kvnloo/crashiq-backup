# CrashIQ — screen principles

Set by the user 2026-10-17. Every UI issue and review checks against these. Theme: `signal-flow-theme` skill.

1. **Every element earns its place.** A button, number, label or line of text stays only if the user needs it
   to decide or act on this screen. If removing it loses nothing, remove it.
2. **One primary action per screen.** It's the green button. Everything else is quieter.
3. **Compact controls for simple choices.** A list of options becomes a dropdown (e.g. years of history),
   not a row of buttons. Unavailable options are hidden, not shown disabled.
4. **One loud element per screen** (the live sim, the 3D map, the pattern replay). It never sits under text:
   text goes beside or above it, never on top.
5. **Detail on demand.** Provenance, table references, rules and settings sit one click away (disclosure,
   tooltip, audit tab), not on the main surface. They're never removed, because traceability is a product rule.
6. **Clear placement.** Content aligns to one grid; nothing overlaps; spacing separates groups instead of boxes.

Sources: the user's `web-design` and `ux-design` skills (Rams, Refactoring UI, Hick's law), `signal-flow-theme` rule 6.
Further reading: github.com/robinstickel/awesome-design-principles.
