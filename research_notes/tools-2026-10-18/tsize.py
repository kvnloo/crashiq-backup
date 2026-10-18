import re, urllib.request, collections, json
units={'K':1e3,'M':1e6,'G':1e9}
out={}
for layer in ["EDGES","FACES","ADDR","FEATNAMES"]:
    h=urllib.request.urlopen(urllib.request.Request(f"https://www2.census.gov/geo/tiger/TIGER2026/{layer}/",headers={"User-Agent":"Mozilla/5.0"}),timeout=60).read().decode()
    rows=re.findall(r'href="tl_2026_(\d{2})(\d{3})_\w+\.zip".*?</td>\s*<td[^>]*>[^<]*</td>\s*<td[^>]*>\s*([\d.]+)([KMG])',h,re.S)
    if not rows:
        print(layer,"parse fail", h[h.find('tl_2026'):h.find('tl_2026')+300]); continue
    s=collections.Counter(); n=collections.Counter()
    for st,co,v,u in rows: s[st]+=float(v)*units[u]; n[st]+=1
    out[layer]={"files":len(rows),"total_GB":round(sum(s.values())/1e9,2),"by_state":{k:round(v/1e9,3) for k,v in s.items()},"counties":dict(n)}
json.dump(out,open("tiger2026_sizes.json","w"))  # run: python3 tsize.py (reads Census TIGER2026 directory listings)
for k,v in out.items(): print(k,v["files"],"files",v["total_GB"],"GB zipped")
states={"06":"CA","48":"TX","36":"NY","53":"WA","25":"MA","42":"PA","12":"FL"}
for f,a in states.items():
    print(a, {k:out[k]["by_state"].get(f) for k in out}, "sum", round(sum(out[k]["by_state"].get(f,0) for k in out),2), "GB zipped")
