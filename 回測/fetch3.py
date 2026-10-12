import urllib.request, json, time
H={'User-Agent':'Mozilla/5.0'}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read())['chart']['result'][0]
now=int(time.time())
for s in ['006208','0056','00878','00631L','00632R']:
    out={'d':get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&period1=0&period2={now}&events=div,split'),
         'h':get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=60m&range=730d'),'m':[]}
    if 'adjclose' not in out['d']['indicators']: out['d']['indicators']['adjclose']=[{'adjclose':out['d']['indicators']['quote'][0]['close']}]
    json.dump(out,open(f'{s}.json','w'))
    t=out['d']['timestamp'];print(s,len(t),time.strftime('%Y-%m-%d',time.localtime(t[0])))
