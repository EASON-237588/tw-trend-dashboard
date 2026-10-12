from bt import *
import datetime as dt, itertools, pickle, collections
def weekly(B):
    out=[];cur=None
    for b in B:
        k=dt.date.fromisoformat(b['d']).isocalendar()[:2]
        if cur is None or cur['k']!=k:
            if cur: out.append(cur)
            cur=dict(b,k=k)
        else: cur['h']=max(cur['h'],b['h']);cur['l']=min(cur['l'],b['l']);cur['c']=b['c'];cur['v']+=b['v']
    out.append(cur);return out
def key(b,tf): return b['t'] if tf=='60分' else (b['d'] if tf=='日線' else b['k'])
def series(s,tf):
    if tf=='60分': return load(s,'h')
    D=load(s,'d'); return D if tf=='日線' else weekly(D)
START={'60分':700,'日線':1300,'週線':260}
def maPos(B,n):
    m=sma([b['c'] for b in B],n); return [1 if (m[i] and B[i]['c']>m[i]) else 0 for i in range(len(B))]
def cfgs(tf):
    c=[]
    for per,mult in itertools.product([5,8,12,20,30,50,80,120,200],[0.5,1,1.5,2,3,4,6,9,13]): c.append(('RF',per,mult))
    for look,stop in itertools.product([5,10,20,30,50,80,120,200],[0,5,8]): c.append(('Don',look,stop))
    for n in [5,10,20,30,40,60,80,100,120,150,200,250]: c.append(('MA',n,0))
    return c
def sig(I,cf):
    if cf[0]=='RF': return calcRF(I,cf[1],cf[2],mode='long',useVol=False)[0]
    if cf[0]=='Don': return calcDon(I,cf[1],'long',cf[2])[0]
    return maPos(I,cf[1])
def yrs(B,a,b): return max((B[b-1]['t']-B[a]['t'])/365.25/86400,0.1)
def cell(B,pos,a,b):
    r=perf(B,pos,a,b); y=yrs(B,a,b)
    pk=0;bm=0
    for i in range(a,b): pk=max(pk,B[i]['c']);bm=max(bm,1-B[i]['c']/pk)
    cg=lambda x:(1+x)**(1/y)-1
    r.update(bm=bm,cal=cg(r['ret'])/max(r['mdd'],.01),bcal=cg(r['bh'])/max(bm,.01),cagr=cg(r['ret']),bcagr=cg(r['bh']));return r
def run(stocks,tf,cf,IDX):
    I=IDX[tf];p=sig(I,cf);m={key(b,tf):p[i] for i,b in enumerate(I)}
    out=[]
    for s in stocks:
        B=SER[(s,tf)];pos=[m.get(key(b,tf),0) for b in B];st=START[tf];mid=(st+len(B))//2
        out+= [cell(B,pos,st,mid),cell(B,pos,mid,len(B))]
    return out
SER={}
ALL=['2330','2317','2884','0050','2454','2412','2881']
for s in ALL:
    for tf in START: SER[(s,tf)]=series(s,tf)
IDX={tf:series('TWII',tf) for tf in START}
if __name__=='__main__':
    rows=[]
    for tf in START:
        for cf in cfgs(tf): rows.append((tf,cf,run(['2330','2317','2884'],tf,cf,IDX)))
    pickle.dump(rows,open('mkt.pkl','wb'))
    sc=lambda cs:(sum(c['ret']>c['bh'] for c in cs),sum(c['cal']>c['bcal'] for c in cs))
    for tf in START:
        R=[(sc(cs),cf,cs) for t,cf,cs in rows if t==tf]
        print('\n===',tf,'報酬贏格數分布',collections.Counter(x[0][0] for x in R),' 年化÷回撤贏格數分布',collections.Counter(x[0][1] for x in R))
        for (a,b),cf,cs in sorted(R,key=lambda x:(-x[0][1],-x[0][0],-min(c['cal']/c['bcal'] for c in x[2])))[:8]:
            print(f"  {cf} 報酬贏{a}/6 比值贏{b}/6 | 年化 "+' '.join(f"{c['cagr']*100:.0f}/{c['bcagr']*100:.0f}" for c in cs)+" | 回撤 "+' '.join(f"{c['mdd']*100:.0f}/{c['bm']*100:.0f}" for c in cs))
