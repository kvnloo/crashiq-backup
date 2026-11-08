import json, urllib.request, urllib.parse, sys
UA={'User-Agent':'CrashIQ/0.1'}
def get(url, **p):
    p.setdefault('f','json')
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url+'?'+urllib.parse.urlencode(p),headers=UA),timeout=180) as r:
                d=json.load(r)
            if 'error' in d: raise RuntimeError(d['error'])
            return d
        except Exception as e:
            err=e
    raise err
OPEN='https://gis.crashdata.dot.mass.gov/arcgis/rest/services/MassDOT/MASSDOT_ODP_OPEN_{}/FeatureServer'
CLOSED='https://gis.massdot.state.ma.us/arcgis/rest/services/CrashClosedYear/CrashClosedYear{}/FeatureServer'
svc={2020:'https://gis.massdot.state.ma.us/arcgis/rest/services/Roads/CrashClosedYears/FeatureServer'}
for y in (2021,2022,2024,2025,2026): svc[y]=OPEN.format(y)
svc[2023]=OPEN.format('2023v')
for y in range(2018,2020): svc[y]=CLOSED.format(y)
out={}
if __name__ != "__main__": raise SystemExit
for y in sorted(svc):
    base=svc[y]+'/0'
    try:
        meta=get(base)
        names=[f['name'] for f in meta['fields']]
        cnt=lambda w: get(base+'/query',where=w,returnCountOnly='true')['count']
        r={'url':base,'n':cnt('1=1')}
        r['geocoded']=cnt("IS_GEOCODED='Yes'") if 'IS_GEOCODED' in names else None
        r['latlon']=cnt("LAT IS NOT NULL AND LAT>41 AND LAT<43.1 AND LON>-73.6 AND LON<-69.8") if 'LAT' in names else None
        r['rdwy']=cnt("RDWY IS NOT NULL AND RDWY<>''") if 'RDWY' in names else None
        r['rdwy_and_int_or_addr']=cnt("RDWY IS NOT NULL AND RDWY<>'' AND ((NEAR_INT_RDWY IS NOT NULL AND NEAR_INT_RDWY<>'') OR (STREET_NUMB IS NOT NULL AND STREET_NUMB<>''))") if 'RDWY' in names else None
        r['street_numb']=cnt("STREET_NUMB IS NOT NULL AND STREET_NUMB<>''") if 'STREET_NUMB' in names else None
        df='CRASH_DATE' if 'CRASH_DATE' in names else 'CRASH_DATETIME'
        st=get(base+'/query',where='1=1',outStatistics=json.dumps([{'statisticType':'max','onStatisticField':df,'outStatisticFieldName':'mx'},{'statisticType':'min','onStatisticField':df,'outStatisticFieldName':'mn'}]))
        a=st['features'][0]['attributes']; r['min_date'],r['max_date']=a['mn'],a['mx']
        g=get(base+'/query',where='1=1',groupByFieldsForStatistics='MAX_INJR_SVRTY_CL',outStatistics=json.dumps([{'statisticType':'count','onStatisticField':'OBJECTID','outStatisticFieldName':'c'}]))
        r['severity']={f['attributes']['MAX_INJR_SVRTY_CL']:f['attributes']['c'] for f in g['features']}
        r['fields']=names
        lays=get(svc[y]); r['layers']=[(l['id'],l['name']) for l in lays.get('layers',[])+lays.get('tables',[])]
    except Exception as e:
        r={'url':base,'error':str(e)[:300]}
    out[y]=r; print(y,{k:v for k,v in r.items() if k!='fields'},flush=True)
json.dump(out,open('year_stats.json','w'),indent=1)
