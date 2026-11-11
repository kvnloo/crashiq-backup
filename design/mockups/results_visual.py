"""Results-visual mockup (user decision 2026-11-10, "2 yea"): builds one standalone HTML page from a study's API answers.

    python design/mockups/results_visual.py <folder with network.json profile.json> <out.html>

Every number on the page is read from the app's own answers (/network, /profile tables T1, T2, T12, T13); this script
only picks, sorts and lays them out. The JSON comes from running the app (any study) and saving those two answers.
"""
import json
import sys
from pathlib import Path

SEV = [("sev_k", "Fatal"), ("sev_a", "Serious injury"), ("sev_b", "Minor injury"), ("sev_c", "Possible injury"),
       ("sev_u", "Injury, level not reported"), ("sev_o", "Property damage only")]
TYPES = ["REAR END", "BROADSIDE", "SIDE SWIPE", "HEAD-ON", "VEHICLE/PEDESTRIAN", "HIT OBJECT", "OTHER"]


def build(src: Path) -> dict:
    net = json.loads((src / "network.json").read_text())
    prof = json.loads((src / "profile.json").read_text())
    tables = {t["id"]: t for t in prof["tables"]}
    t1 = {r["key"]: r["values"]["value"] for r in tables["T1"]["rows"]}
    types = {r["key"]: r["values"] for r in tables["T13"]["rows"]}
    flags: dict[str, list] = {}
    for r in tables["T12"]["rows"]:
        loc = r["key"].split("~")[0]
        v = r["values"]
        flags.setdefault(loc, []).append({"what": v["crash_type"], "here": v["target_crashes"], "of": v["location_crashes"],
                                          "share": v["share_pct"], "ref": v["reference_share_pct"],
                                          "strength": v["strength"]})
    ix = {i["id"]: i for i in net["intersections"]}
    locs = []
    for r in tables["T2"]["rows"]:
        v = r["values"]
        if v["kind"] == "intersection":
            i = ix[r["key"]]
            lat, lon, station = i["lat"], i["lon"], i["station_ft"]
        else:
            s = next(s for s in net["segments"] if s["id"] == r["key"])
            a, b = ix[s["from_id"]], ix[s["to_id"]]
            lat, lon = (a["lat"] + b["lat"]) / 2, (a["lon"] + b["lon"]) / 2
            station = (s["from_station_ft"] + s["to_station_ft"]) / 2
        locs.append({"id": r["key"], "label": r["label"], "kind": v["kind"], "lat": lat, "lon": lon, "station": station,
                     "crashes": v["crashes"], "ksi": v["ksi_crashes"], "injury": v["injury_crashes"],
                     "sev": {k: v[k] for k, _ in SEV}, "rate": v["rate"], "critical": v["critical_rate"],
                     "over_critical": v["over_critical"], "types": types.get(r["key"], {}), "flags": flags.get(r["key"], [])})
    w = prof["window"]
    return {"corridor": net["corridor_name"], "length_ft": net["length_ft"], "length_mi": net["length_mi"],
            "line": net["line"], "total": t1["crashes"], "ksi": t1["ksi_crashes"], "injury": t1["injury_crashes"],
            "pdo": t1["pdo_crashes"], "from": w["from_year"], "to": w["to_year"], "years": w["years_with_data"],
            "source": prof["source_short"], "locs": locs}


def headline(d: dict) -> str:
    """Plain sentence; its numbers are T2/T1 values, nothing computed beyond picking the top two intersections."""
    top = sorted((loc for loc in d["locs"] if loc["kind"] == "intersection"), key=lambda x: -x["crashes"])[:2]
    a, b = top
    return (f"{a['label']} and {b['label']} have the most crashes of any intersections on {d['corridor']}: "
            f"{a['crashes']} and {b['crashes']} of the corridor's {d['total']}.")


def main(src: str, out: str) -> None:
    d = build(Path(src))
    d["headline"] = headline(d)
    html = TEMPLATE.replace("__DATA__", json.dumps(d))
    Path(out).write_text(html, encoding="utf-8")
    print(out, len(d["locs"]), "locations,", d["total"], "crashes")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CrashIQ results: visual mockup</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link href="https://fonts.googleapis.com/css2?family=Overpass:wght@400;600;800&family=Overpass+Mono&display=swap" rel="stylesheet">
<style>
:root{--bg:#0D1013;--surface:#151A1F;--surface-2:#1B2127;--line:#29323B;--fg:#E6EAEE;--muted:#8E9AA6;--go:#1EE39A;
--amber:#FFB020;--stop:#FF5A4E;--info:#5AA2FF;--pdo:#5B6672;--minor:#FFB020;--ksi:#FF5A4E;
--font:"Overpass",system-ui,sans-serif;--mono:"Overpass Mono",ui-monospace,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--font)}
header{padding:18px 24px 6px}.eyebrow{font:600 12px var(--mono);letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
h1{font-size:26px;line-height:1.25;margin:6px 0 4px;max-width:1100px;font-weight:800}
.sub{color:var(--muted);font-size:14px}.sub b{color:var(--fg)}
main{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:14px;padding:12px 24px}
#map{height:520px;border-radius:6px;border:1px solid var(--line);background:#111}
aside{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:16px;overflow:auto;max-height:520px}
aside h2{margin:0 0 2px;font-size:18px}.kind{color:var(--muted);font:12px var(--mono);text-transform:uppercase}
.sevbar{display:flex;height:10px;border-radius:3px;overflow:hidden;margin:10px 0 4px;background:var(--surface-2)}
.legend{display:flex;gap:14px;font-size:12px;color:var(--muted);flex-wrap:wrap}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.types{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}
.type{background:var(--surface-2);border-radius:6px;padding:8px;display:flex;gap:8px;align-items:center}
.type svg{flex:none}.type b{font-size:20px;display:block}.type span{font-size:12px;color:var(--muted)}
.flag{border-left:3px solid var(--amber);padding:6px 10px;margin-top:10px;background:var(--surface-2);font-size:13px}
.flag small{color:var(--muted);display:block}
.strip{margin:0 24px 24px;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:12px 16px}
.strip h3{margin:0 0 6px;font-size:13px;color:var(--muted);font-weight:600}
.strip svg{width:100%;min-width:900px;height:150px;display:block}.note{font-size:12px;color:var(--muted);margin-top:4px}
.col{cursor:pointer}.dark-tiles{filter:invert(1) hue-rotate(180deg) brightness(.85) contrast(.9) saturate(.3)}.leaflet-container{font-family:var(--font)}
@media (max-width:900px){.maplegend{display:none}main{grid-template-columns:1fr}#map{height:380px}aside{max-height:none}}
</style></head><body>
<header><div class="eyebrow">Crash profile · <span id="corr"></span> · mockup on real data</div>
<h1 id="headline"></h1><div class="sub" id="sub"></div></header>
<main><div id="map"></div><aside id="panel"></aside></main>
<section class="strip"><h3>Along the corridor, south to north: each intersection's crashes, with the over-represented patterns flagged</h3>
<div style="overflow-x:auto"><svg id="strip"></svg></div><div class="note" id="stripnote"></div></section>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const D = __DATA__;
const SEV=[["sev_k","Fatal","var(--ksi)"],["sev_a","Serious injury","var(--ksi)"],["sev_b","Minor injury","var(--minor)"],
["sev_c","Possible injury","#C98A1A"],["sev_u","Injury, level not reported","#C98A1A"],["sev_o","Property damage only","var(--pdo)"]];
const yrs = D.years===D.to-D.from+1 ? `${D.from}–${D.to}` : `${D.from}–${D.to} (${D.years} years with data)`;
document.getElementById('corr').textContent=D.corridor;
document.getElementById('headline').textContent=D.headline;
document.getElementById('sub').innerHTML=`<b>${D.total}</b> crashes on ${D.length_mi.toFixed(2)} mi, ${yrs}, ${D.source}: <b style="color:var(--ksi)">${D.ksi}</b> fatal or serious injury · <b style="color:var(--minor)">${D.injury-D.ksi}</b> other injury · <b>${D.pdo}</b> property damage only`;
const maxC=Math.max(...D.locs.map(l=>l.crashes));
function column(l,len,west){ // severity bar off the corridor: worst outcomes nearest the street
  let x=0, parts=''; const tot=l.crashes||1;
  for(const [k,,c] of SEV){const n=l.sev[k]; if(!n) continue; const s=len*n/tot; parts+=`<rect x="${west?len-x-s:x}" y="0" width="${s}" height="12" fill="${c}"/>`; x+=s;}
  const lab=`<text x="${west?-6:len+6}" y="11" text-anchor="${west?'end':'start'}" font-size="12" font-weight="700" fill="#E6EAEE">${l.crashes}</text>`;
  return `<svg width="${len}" height="12" style="overflow:visible">${parts}${lab}</svg>`;
}
const map=L.map('map',{zoomControl:false,attributionControl:true});
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19,className:'dark-tiles'}).addTo(map);
L.polyline(D.line,{color:'#E9E4D4',weight:3,opacity:.5}).addTo(map);
map.fitBounds(L.latLngBounds(D.line).pad(.12));
const lg=L.control({position:'topleft'}); lg.onAdd=()=>{const d=L.DomUtil.create('div','maplegend');d.style.cssText='background:#151A1FE6;border:1px solid #29323B;border-radius:6px;padding:8px 10px;font-size:12px;color:#E6EAEE;line-height:1.6';
 d.innerHTML='<b>Crashes per location</b><br>bars right of the street: intersections<br>bars left: the block between<br><span style="color:var(--ksi)">■</span> fatal / serious <span style="color:var(--minor)">■</span> injury <span style="color:#8E9AA6">■</span> damage only';return d}; lg.addTo(map);
const markers={};
for(const l of D.locs.filter(l=>l.crashes>0)){ const len=Math.max(4,160*l.crashes/maxC), west=l.kind==='segment'; // intersections east, blocks west
  const icon=L.divIcon({className:'col',html:column(l,len,west),iconSize:[len,12],iconAnchor:[west?len+8:-8,6]});
  markers[l.id]=L.marker([l.lat,l.lon],{icon}).addTo(map).on('click',()=>select(l.id)); }
const G={ // tiny collision-diagram glyphs, one per collision type
 "REAR END":'<path d="M20 34V8M20 8l-5 6M20 8l5 6" /><path d="M20 52V40M20 40l-5 6M20 40l5 6"/>',
 "BROADSIDE":'<path d="M24 54V12M24 12l-5 6M24 12l5 6"/><path d="M4 30h30M34 30l-6-5M34 30l-6 5"/>',
 "SIDE SWIPE":'<path d="M16 54V8M16 8l-5 6M16 8l5 6"/><path d="M28 54V18M28 18l-5 6M28 18l5 6"/>',
 "HEAD-ON":'<path d="M20 54V34M20 34l-5-6M20 34l5-6" transform="rotate(180 20 44)"/><path d="M20 4v20M20 24l-5-6M20 24l5-6"/>',
 "VEHICLE/PEDESTRIAN":'<path d="M18 54V14M18 14l-5 6M18 14l5 6"/><circle cx="34" cy="26" r="4"/><path d="M34 30v12M28 36h12"/>',
 "HIT OBJECT":'<path d="M20 54V18M20 18l-5 6M20 18l5 6"/><rect x="12" y="4" width="16" height="7"/>',
 "OTHER":'<circle cx="22" cy="30" r="12"/><path d="M22 24v8M22 36v1"/>'};
function select(id){ const l=D.locs.find(x=>x.id===id); const P=document.getElementById('panel');
  const bar=SEV.map(([k,n,c])=>l.sev[k]?`<div title="${n}: ${l.sev[k]}" style="width:${100*l.sev[k]/l.crashes}%;background:${c}"></div>`:'').join('');
  const types=Object.entries(l.types).filter(([k,v])=>k!=='total'&&v>0).sort((a,b)=>b[1]-a[1]).map(([k,v])=>
    `<div class="type"><svg width="40" height="58" viewBox="0 0 44 58" fill="none" stroke="#E6EAEE" stroke-width="2.4" stroke-linecap="round">${G[k]||G.OTHER}</svg><div><b>${v}</b><span>${k.toLowerCase().replace('vehicle/pedestrian','pedestrian')}</span></div></div>`).join('');
  const rate = l.rate==null ? `<div class="note">Crash rate vs critical rate: needs the daily traffic (AADT) for this location.</div>`
    : `<div class="note">Crash rate ${l.rate} vs critical ${l.critical}${l.over_critical?' · <b style="color:var(--stop)">over critical</b>':''}</div>`;
  const flags=l.flags.map(f=>`<div class="flag">${f.what}: <b>${f.here} of ${f.of}</b> crashes here (${f.share}%) vs ${f.ref}% on the rest of the corridor<small>${f.strength} evidence · over-represented screen</small></div>`).join('');
  P.innerHTML=`<div class="kind">${l.kind}</div><h2>${l.label}</h2><div class="sub"><b>${l.crashes}</b> crashes · <b style="color:var(--ksi)">${l.ksi}</b> fatal/serious · ${l.injury} injury</div>
   <div class="sevbar">${bar}</div><div class="legend"><span><i style="background:var(--ksi)"></i>fatal / serious</span><span><i style="background:var(--minor)"></i>injury</span><span><i style="background:var(--pdo)"></i>damage only</span></div>
   ${rate}${flags}<div class="kind" style="margin-top:16px">Collision types (crash diagram)</div><div class="types">${types||'<span class="note">No crashes.</span>'}</div>`;
  for(const [k,m] of Object.entries(markers)) m.setOpacity(k===id?1:.45);
  drawStrip(id);
}
function drawStrip(sel){ const S=document.getElementById('strip'); const W=S.clientWidth||1200, H=150, pad=40;
  const x=s=>pad+(W-pad-110)*s/D.length_ft; /* right margin: the slanted names run up-right */ let g=`<line x1="${pad}" x2="${W-pad}" y1="90" y2="90" stroke="#29323B" stroke-width="10" stroke-linecap="round"/>`;
  for(const l of D.locs.filter(l=>l.kind==='segment')){ const w=Math.max(2,14*l.crashes/maxC);
    g+=`<g class="col" onclick="select('${l.id}')"><line x1="${x(l.station)-30}" x2="${x(l.station)+30}" y1="90" y2="90" stroke="${l.ksi?'var(--ksi)':'#8E9AA6'}" stroke-width="${w}" opacity="${l.id===sel?1:.6}"/><text x="${x(l.station)}" y="110" text-anchor="middle" font-size="11" fill="#8E9AA6">${l.crashes}</text></g>`;}
  for(const l of D.locs.filter(l=>l.kind==='intersection')){ const r=5+16*Math.sqrt(l.crashes/maxC), on=l.id===sel;
    const fill=l.ksi?'var(--ksi)':l.injury?'var(--minor)':'var(--pdo)';
    g+=`<g class="col" onclick="select('${l.id}')"><circle cx="${x(l.station)}" cy="90" r="${r}" fill="${fill}" stroke="${on?'#fff':'#0D1013'}" stroke-width="${on?3:2}"/>
      <text x="${x(l.station)}" y="94" text-anchor="middle" font-size="11" font-weight="800" fill="#0D1013">${l.crashes}</text>
      ${l.flags.length?`<text x="${x(l.station)}" y="${90+r+28}" text-anchor="middle" font-size="12" fill="var(--amber)">▲${l.flags.length}</text>`:''}
      <text x="${x(l.station)+4}" y="58" text-anchor="start" font-size="11" fill="${on?'#E6EAEE':'#8E9AA6'}" transform="rotate(-28 ${x(l.station)+4} 58)">${l.label.length>26?l.label.slice(0,25)+'…':l.label}</text></g>`;}
  S.innerHTML=g;
  document.getElementById('stripnote').textContent='Circle size = crashes · red = has a fatal or serious-injury crash, amber = injury, grey = damage only · ▲ = over-represented patterns · bars between = crashes on the block between intersections. Crash rate vs critical rate shows once the daily traffic is entered.';
}
select([...D.locs].filter(l=>l.kind==='intersection').sort((a,b)=>b.crashes-a.crashes)[0].id);
addEventListener('resize',()=>drawStrip(document.querySelector('aside h2')&&D.locs.find(l=>l.label===document.querySelector('aside h2').textContent)?.id));
</script></body></html>"""

if __name__ == "__main__":
    main(*sys.argv[1:3])
