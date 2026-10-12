import json, datetime as dt, math
TZ=dt.timezone(dt.timedelta(hours=8))
def day(t): return dt.datetime.fromtimestamp(t,TZ).strftime('%Y-%m-%d')
def load(s, kind='h'):
    J=json.load(open(f'{s}.json'))
    d=J['d']; q=d['indicators']['quote'][0]; ac=d['indicators']['adjclose'][0]['adjclose']
    fac={}
    for t,c,a in zip(d['timestamp'],q['close'],ac):
        if c and a: fac[day(t)]=a/c
    if kind=='d': src=[d]
    elif kind=='h': src=[J['h']]
    else: src=J['m']
    B=[];seen=set()
    for r in src:
        q=r['indicators']['quote'][0]
        for i,t in enumerate(r.get('timestamp') or []):
            o,h,l,c,v=(q[k][i] for k in ('open','high','low','close','volume'))
            if None in (o,h,l,c) or t in seen: continue
            seen.add(t); f=fac.get(day(t),1.0)
            B.append(dict(t=t,o=o*f,h=h*f,l=l*f,c=c*f,v=v or 0,d=day(t)))
    B.sort(key=lambda b:b['t'])
    if kind=='d': B=repair(B, 0.205 if s.endswith('L') else 0.105)
    return B
LOG=[]
def repair(B, lim=0.105):
    """Yahoo 分割還原錯日期：超過漲跌幅上限且之後停在新水準 → 之前整段等比例調整；隔天彈回 → 刪掉該日"""
    i=1
    while i<len(B):
        r=B[i]['c']/B[i-1]['c']-1
        if abs(r)>lim:
            if i+1<len(B) and abs(B[i+1]['c']/B[i-1]['c']-1)<lim:
                LOG.append(('刪單日',B[i]['d'],round(r,3))); B.pop(i); continue
            f=B[i]['c']/B[i-1]['c']; LOG.append(('等比調整',B[i]['d'],round(f,4)))
            for b in B[:i]:
                for k in 'ohlc': b[k]*=f
        i+=1
    return B
def agg(B, mins):
    """把 1 分 K 合成 N 分（每天 09:00 重新起算）"""
    out=[];cur=None
    for b in B:
        x=dt.datetime.fromtimestamp(b['t'],TZ); k=(b['d'],((x.hour-9)*60+x.minute)//mins)
        if cur is None or cur['k']!=k:
            if cur: out.append(cur)
            cur=dict(b,k=k)
        else: cur['h']=max(cur['h'],b['h']);cur['l']=min(cur['l'],b['l']);cur['c']=b['c'];cur['v']+=b['v']
    if cur: out.append(cur)
    return out
# ---- 照儀表板移植 ----
def pineMA(src,n,alpha):
    out=[None]*len(src);prev=None;s=0;cnt=0
    for i,v in enumerate(src):
        if v is None: out[i]=prev;continue
        if prev is None:
            s+=v;cnt+=1
            if cnt==n: prev=s/n;out[i]=prev
        else: prev=alpha*v+(1-alpha)*prev;out[i]=prev
    return out
ema=lambda s,n:pineMA(s,n,2/(n+1)); rma=lambda s,n:pineMA(s,n,1/n)
def sma(src,n):
    out=[None]*len(src);s=0
    for i in range(len(src)):
        s+=src[i]
        if i>=n: s-=src[i-n]
        if i>=n-1: out[i]=s/n
    return out
def tr(B): return [b['h']-b['l'] if i==0 else max(b['h']-b['l'],abs(b['h']-B[i-1]['c']),abs(b['l']-B[i-1]['c'])) for i,b in enumerate(B)]
def rmax(x,n):
    out=[None]*len(x);dq=[]
    for i in range(len(x)):
        if i>=n: out[i]=x[dq[0]]
        while dq and x[dq[-1]]<=x[i]: dq.pop()
        dq.append(i)
        if dq[0]<=i-n: dq.pop(0)
    return out
def rmin(x,n): return [None if v is None else -v for v in rmax([-v for v in x],n)]
def calcRF(B,per,mult,useAtr=True,atrLen=12,atrMult=1.5,useVol=True,volLen=20,mode='both'):
    n=len(B);src=[(b['h']+b['l'])/2 for b in B]
    diff=[None]+[abs(src[i]-src[i-1]) for i in range(1,n)]
    av=ema(diff,per);sm=[None if v is None else v*mult for v in ema(av,per*2-1)]
    filt=[None]*n;prev=None
    for i in range(n):
        x,r=src[i],sm[i]
        if r is None: prev=None;continue
        pv=0 if prev is None else prev
        filt[i]=prev=(pv if x-r<pv else x-r) if x>pv else (pv if x+r>pv else x+r)
    atr=rma(tr(B),atrLen);vm=sma([b['v'] for b in B],volLen)
    pos=[0]*n;up=dn=0;ci=None;cur=0
    for i in range(n):
        f=filt[i];pf=filt[i-1] if i else None
        if f is not None and pf is not None:
            up=up+1 if f>pf else (0 if f<pf else up); dn=dn+1 if f<pf else (0 if f>pf else dn)
        s=src[i];ps=src[i-1] if i else None;moved=ps is not None and s!=ps
        lc=f is not None and s>f and moved and up>0; sc=f is not None and s<f and moved and dn>0
        a=atr[i];c=B[i]['c']
        lf=(not useAtr) or (a is not None and c>c-a*atrMult); sf=(not useAtr) or (a is not None and c<c+a*atrMult)
        vok=(not useVol) or (vm[i] is not None and B[i]['v']>vm[i]*0.8)
        ls=lc and lf and vok; ss=sc and sf and vok
        pci=ci; ci=1 if ls else (-1 if ss else pci)
        if ls and pci==-1: cur=1
        elif ss and pci==1: cur=-1
        pos[i]=cur
    if mode=='long': pos=[1 if p>0 else 0 for p in pos]
    return pos, 6*per
def calcDon(B,look,mode='long',stopAtr=8,atrLen=14):
    n=len(B);exitN=max(10,round(look/3));Hh=[b['h'] for b in B];Ll=[b['l'] for b in B]
    hh,ll,he,le=rmax(Hh,look),rmin(Ll,look),rmax(Hh,exitN),rmin(Ll,exitN)
    atr=rma(tr(B),atrLen);rev=mode=='both';pos=[0]*n;dr=0;side=0;avg=None
    for i in range(n):
        c=B[i]['c']
        if hh[i] is not None and c>hh[i] and mode!='short': dr=1
        elif ll[i] is not None and c<ll[i] and mode!='long': dr=-1
        elif not rev and dr==1 and le[i] is not None and c<le[i]: dr=0
        elif not rev and dr==-1 and he[i] is not None and c>he[i]: dr=0
        flip=dr!=0 and dr!=side
        if not rev and side!=0 and atr[i] and stopAtr and (avg-c)*side>=stopAtr*atr[i]: side=0;avg=None;dr=0
        if not rev and dr==0 and side!=0: side=0;avg=None
        if flip: side=dr;avg=c
        pos[i]=side
    return pos, look
# ---- 績效：收盤成交，持倉跟著下一根報酬 ----
def perf(B,pos,start,end=None,cost=0.0038):
    end=end or len(B); eq=1.0;peak=1.0;mdd=0;trades=[];ent=None;p=0
    for i in range(start,end):
        if i>start:
            r=B[i]['c']/B[i-1]['c']-1; eq*=1+p*r
        np_=pos[i] if i<end-1 else p
        if np_!=p:
            eq*=1-abs(np_-p)*cost/2
            if p!=0: trades.append((B[i]['c']/ent-1)*p - cost)
            ent=B[i]['c'] if np_!=0 else None; p=np_
        peak=max(peak,eq);mdd=max(mdd,1-eq/peak)
    if p!=0: trades.append((B[end-1]['c']/ent-1)*p-cost)
    bh=B[end-1]['c']/B[start]['c']-1
    win=sum(1 for x in trades if x>0)
    return dict(ret=eq-1,bh=bh,n=len(trades),win=win,mdd=mdd)
