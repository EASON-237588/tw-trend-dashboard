import urllib.request, json, time
H={'User-Agent':'Mozilla/5.0'}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read())['chart']['result'][0]
now=int(time.time())
for s,y in [('TWII','%5ETWII'),('0050','0050.TW'),('2454','2454.TW'),('2412','2412.TW'),('2881','2881.TW')]:
    out={'d':get(f'https://query1.finance.yahoo.com/v8/finance/chart/{y}?interval=1d&period1=0&period2={now}&events=div,split'),
         'h':get(f'https://query1.finance.yahoo.com/v8/finance/chart/{y}?interval=60m&range=730d'),'m':[]}
    if 'adjclose' not in out['d']['indicators']: out['d']['indicators']['adjclose']=[{'adjclose':out['d']['indicators']['quote'][0]['close']}]
    json.dump(out,open(f'{s}.json','w'))
    t=out['d']['timestamp'];print(s,len(t),time.strftime('%Y-%m-%d',time.localtime(t[0])),'60分',len(out['h']['timestamp']))
