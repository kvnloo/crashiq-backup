"""Severity colours: one K/A/B/C/O ramp for every view and export (#108).

Ordered warm to cool so the eye goes to the worst first (PM review, round 2): K red, the strongest; A orange;
B amber; C a muted teal; O a quiet neutral grey, because property damage is about half of all crashes and must not
be the loudest mark. U ("injured, level not stated") is not a level: it's drawn hollow (an outline in this grey),
never as a filled colour.

Dataviz validator (OKLab ΔE×100, Machado CVD) on the dark surface #14181C: every pair, not only neighbours, is
≥ 8.8 apart for protan/deutan and ≥ 15.2 for normal vision; all ≥ 3:1 contrast. On white (exports) the separations
are the same; orange, amber and teal sit under 3:1, which is fine there because exports always pair the swatch with
its label. The lightness-band and chroma-floor checks "fail" by design: bright warm steps and a neutral grey are the
point of an emphasis ramp. The frontend mirrors these in frontend/src/lib/severity.js and the --sev-* tokens in
app.css; tests/test_severity_colors.py keeps all three identical.
"""

from __future__ import annotations

COLORS = {"K": "#e62b34", "A": "#fd811b", "B": "#f6c330", "C": "#5dacba", "U": "#8e9aa6", "O": "#686c71"}
LABELS = {"K": "Fatal", "A": "Serious injury", "B": "Minor injury", "C": "Possible injury",
          "U": "Injury, level not stated", "O": "Property damage"}
