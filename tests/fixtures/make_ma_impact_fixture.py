"""Records tests/fixtures/ma_impact_2025.json: 60 real IMPACT 2025 Middlesex crashes and their persons, cut to the
importer's fields, from the placement sample's recorded responses (research_notes/ma-2026-11-07/fetch_sample.py writes
them; pulled 2026-11-07 23:03 PST). PYTHONPATH=backend python tests/fixtures/make_ma_impact_fixture.py <sample dir>"""
import json
import random
import sys
from pathlib import Path

from crashiq.sources import ma_impact as m

src = Path(sys.argv[1])
crashes = json.loads((src / "sample_middlesex_2025.json").read_text())
persons = json.loads((src / "sample_middlesex_2025_persons.json").read_text())
random.seed(7)
pick = random.sample(crashes, 60)
nums = {c["CRASH_NUMB"] for c in pick}
out = {"service": {"layers": [{"id": 0, "name": "Crash"}, {"id": 1, "name": "Vehicle"}, {"id": 2, "name": "Person"}]},
       "crashes": [{k: c.get(k) for k in m.CRASH_FIELDS} for c in pick],
       "persons": [{k: p.get(k) for k in m.PERSON_FIELDS} for p in persons if p["CRASH_NUMB"] in nums]}
Path(__file__).with_name("ma_impact_2025.json").write_text(json.dumps(out, indent=0))
print(len(out["crashes"]), len(out["persons"]))
