from bt import *
from big import CF
import itertools, pickle
I=load('TWII','h'); D=load('TWII','d')
dc={b['d']:b['c'] for b in D}
# 每天最後一根 60 分 K 改用官方收盤（含 13:30 集合競價）；昨收用「上一個有 60 分資料的交易日」
for i,b in enumerate(I):
    if (i+1==len(I) or I[i+1]['d']!=b['d']) and b['d'] in dc:
        b['c']=dc[b['d']]; b['h']=max(b['h'],b['c']); b['l']=min(b['l'],b['c'])
hd=sorted(set(b['d'] for b in I)); prev={hd[i]:dc[hd[i-1]] for i in range(1,len(hd))}; prev[hd[0]]=I[0]['o']
# 每根 60 分 K 的正2、反1 報酬（每日重設：以昨收為基準）
def legs(I):
    R2=[0];RI=[0];R1=[0]
    for i in range(1,len(I)):
        b,a=I[i],I[i-1]
        base=a['c'] if a['d']==b['d'] else prev[b['d']]
        # 正2 當日淨值 = 1+2*(c/pc-1)，相鄰兩根的比
        pc=prev[b['d']]
        f=lambda x,L:1+L*(x/pc-1)
        prevv=(lambda L:f(a['c'],L)) if a['d']==b['d'] else (lambda L:1.0)
        nd=a['d']!=b['d']
        R2.append(f(b['c'],2)/prevv(2)-1+(0.035/252 if nd else 0))
        RI.append(f(b['c'],-1)/prevv(-1)-1-(0.04/252 if nd else 0))
        R1.append(b['c']/a['c']-1+(0.03/252 if nd else 0))
    return R2,RI,R1
def grp(I,n):
    if n==1: return I,list(range(len(I)))
    out=[];idx=[];cur=None
    for i,b in enumerate(I):
        h=dt.datetime.fromtimestamp(b['t'],TZ).hour; k=(b['d'],(h-9)//n)
        if cur and cur['k']==k: cur['h']=max(cur['h'],b['h']);cur['l']=min(cur['l'],b['l']);cur['c']=b['c'];cur['v']+=b['v'];idx[-1]=i
        else:
            cur=dict(b,k=k);out.append(cur);idx.append(i)
    return out,idx
R2,RI,R1=legs(I)
ST=700
def run(G,ix,pos,bear,lag=0,cost=0.0018,a=ST,b=None):
    b=b or len(I)
    if lag: pos=[0]*lag+pos[:-lag]
    dp=[0]*len(I)
    for k in range(len(G)-1):
        for j in range(ix[k]+1,ix[k+1]+1): dp[j]=pos[k]
    eq=pk=1;mdd=0;prv=dp[a];tr=0
    for j in range(a+1,b):
        p=dp[j]
        if p!=prv: eq*=1-cost/2*(abs(p-prv) if bear=='-1' else abs((p>0)-(prv>0)));tr+=1
        prv=p; eq*=1+(R2[j] if p>0 else (RI[j] if p<0 and bear=='-1' else 0)); pk=max(pk,eq);mdd=max(mdd,1-eq/pk)
    y=(I[b-1]['t']-I[a]['t'])/365.25/86400
    return eq**(1/y)-1,mdd,tr
import datetime as dt
if __name__=='__main__':
    rows=[]
    for n,tf in [(1,'60分'),(2,'2小時')]:
        G,ix=grp(I,n)
        for cf in CF:
            w=(6*cf[1] if cf[0]=='RF' else cf[1])*n
            if w>ST: continue
            if cf[0]=='RF': p=calcRF(G,cf[1],cf[2],useVol=False)[0]
            elif cf[0]=='Don': p=calcDon(G,cf[1],'both',0)[0]
            else:
                m=sma([b['c'] for b in G],cf[1]); p=[(1 if G[i]['c']>m[i] else -1) if m[i] else 0 for i in range(len(G))]
            for bear in ('0','-1'): rows.append((tf,cf,bear,run(G,ix,p,bear),run(G,ix,p,bear,1)))
    e=1
    for j in range(ST+1,len(I)): e*=1+R1[j]
    y=(I[-1]['t']-I[ST]['t'])/365.25/86400
    pickle.dump((rows,e**(1/y)-1,I[ST]['d']),open('bigh.pkl','wb'))
