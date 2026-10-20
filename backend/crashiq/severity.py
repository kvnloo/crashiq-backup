"""Severity colours: one K/A/B/C/O ramp for every view and export (#108).

Validated with the dataviz palette validator (OKLab ΔE×100, Machado CVD simulation) on the app's dark surface
#14181C and on white (exports): every adjacent pair passes for normal vision (≥ 19.4) and protan/deutan (≥ 11.4);
all pairs stay ≥ 7.5 colour-blind (the 6–8 band, legal with the secondary encodings we keep: bigger K/A marks,
direct labels, tables) and ≥ 19.4 normal; all ≥ 3:1 contrast on both surfaces. U ("injured, level not stated") is a
neutral grey on purpose: it's an unknown, not a level. The frontend mirrors these in frontend/src/lib/severity.js and
the --sev-* tokens in app.css; tests/test_severity_colors.py keeps all three identical.
"""

from __future__ import annotations

COLORS = {"K": "#d9003b", "A": "#d37e01", "B": "#666800", "C": "#19a0b8", "U": "#8e9aa6", "O": "#6f57ab"}
LABELS = {"K": "Fatal", "A": "Serious injury", "B": "Minor injury", "C": "Possible injury",
          "U": "Injury, level not stated", "O": "Property damage"}
