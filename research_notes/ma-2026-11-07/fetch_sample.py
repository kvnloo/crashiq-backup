import json,urllib.request,urllib.parse,random,time
UA={'User-Agent':'CrashIQ/0.1'}
B='https://gis.crashdata.dot.mass.gov/arcgis/rest/services/MassDOT/MASSDOT_ODP_OPEN_2025/FeatureServer/'
def post(layer,**p):
    p['f']='json'
    for i in range(5):
        try:
            req=urllib.request.Request(B+f'{layer}/query',data=urllib.parse.urlencode(p).encode(),headers=UA)
            d=json.load(urllib.request.urlopen(req,timeout=300))
            if 'error' in d: raise RuntimeError(d['error'])
            return d
        except Exception as e:
            err=e; time.sleep(5*(i+1))
    raise err
ids=post(0,where="CNTY_NAME='MIDDLESEX'",returnIdsOnly='true')['objectIds']
print('middlesex ids',len(ids))
random.seed(20251107); pick=sorted(random.sample(ids,2000))
rows=[]
for i in range(0,len(pick),200):
    d=post(0,objectIds=','.join(map(str,pick[i:i+200])),outFields='*',returnGeometry='false')
    rows+= [f['attributes'] for f in d['features']]
print('rows',len(rows))
json.dump(rows,open('sample_middlesex_2025.json','w'))
nums=[r['CRASH_NUMB'] for r in rows]
pers=[]
for i in range(0,len(nums),100):
    d=post(2,where='CRASH_NUMB IN (%s)'%','.join(map(str,nums[i:i+100])),outFields='CRASH_NUMB,PERS_NUMB,VEHC_UNIT_NUMB,INJY_STAT_DESCR,PERS_TYPE,AGE,SEX_DESCR,NON_MTRST_TYPE_DESCR',returnGeometry='false',resultRecordCount=2000)
    pers+=[f['attributes'] for f in d['features']]
    if d.get('exceededTransferLimit'): print('WARN exceeded',i)
print('persons',len(pers))
json.dump(pers,open('sample_middlesex_2025_persons.json','w'))
