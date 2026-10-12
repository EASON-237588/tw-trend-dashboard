import urllib.request, json, time
H={'User-Agent':'Mozilla/5.0'}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read())['chart']['result'][0]
now=int(time.time())
for s in ['2330','2317','2884']:
    out={}
    out['d']=get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&period1=0&period2={now}&events=div,split')
    out['h']=get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=60m&range=730d')
    m=[]
    for k in range(4,-1,-1):
        p2=now-k*7*86400; p1=max(p2-7*86400, now-29*86400)
        if p1>=p2: continue
        try: m.append(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1m&period1={p1}&period2={p2}'))
        except Exception as e: print(s,'1m',k,e)
    out['m']=m
    json.dump(out,open(f'{s}.json','w'))
    print(s,'日線',len(out['d']['timestamp']),'60分',len(out['h']['timestamp']),'1分段',[len(x.get('timestamp') or []) for x in m])
