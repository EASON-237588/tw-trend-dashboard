import urllib.request, json, time, os
H={'User-Agent':'Mozilla/5.0'}
now=int(time.time())
L=['0050','006208','0051','0052','0053','0055','00692','00850','00881','0056','00713','00878','00900','00919','00929','00939','00940','00891','00631L','00663L','00675L','00685L']
for s in L:
    if os.path.exists(f'{s}.json') and s not in ('0050',): 
        j=json.load(open(f'{s}.json'))
        if 'd' in j: print(s,'已有');continue
    try:
        r=json.loads(urllib.request.urlopen(urllib.request.Request(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}.TW?interval=1d&period1=0&period2={now}&events=div,split',headers=H),timeout=30).read())['chart']['result'][0]
        if 'adjclose' not in r['indicators']: r['indicators']['adjclose']=[{'adjclose':r['indicators']['quote'][0]['close']}]
        json.dump({'d':r,'h':r,'m':[]},open(f'{s}.json','w'))
        print(s,len(r['timestamp']),time.strftime('%Y-%m-%d',time.localtime(r['timestamp'][0])))
    except Exception as e: print(s,'失敗',e)
    time.sleep(0.5)
