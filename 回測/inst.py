import json, itertools
from bt import load, calcRF
T=load('TWII','d'); D=[b['d'] for b in T]
rf=calcRF(T,15,4,useVol=False)[0]; RF=[1 if p==1 else 0 for p in rf]
raw=json.load(open('inst.json')); net={}
for x in raw:
    k={'Foreign_Investor':'外資','Investment_Trust':'投信','total':'合計'}.get(x['name'])
    if k: net.setdefault(k,{})[x['date']]=x['buy']-x['sell']
r=[0]+[T[i]['c']/T[i-1]['c']-1 for i in range(1,len(T))]
R2=[0]+[2*x+0.035/252 for x in r[1:]]
SEG=[('2004-06-01','2008-12-31'),('2009-01-01','2017-12-31'),('2018-01-01','2026-12-31'),('2004-06-01','2026-12-31')]
def ev(pos,cost=0.0018):
    out=[]
    for a,b in SEG:
        ia=next(i for i,d in enumerate(D) if d>=a); ib=max(i for i,d in enumerate(D) if d<=b)
        eq=pk=1;mdd=0;n=0
        for j in range(ia+1,ib+1):
            p,pp=pos[j-1],(pos[j-2] if j>=2 else 0)
            if p!=pp: eq*=1-cost/2; n+=p>pp
            eq*=1+(R2[j] if p else 0); pk=max(pk,eq); mdd=max(mdd,1-eq/pk)
        y=(len(range(ia,ib)))/252
        out.append((eq**(1/y)-1,mdd,n))
    return out
def instsig(k,N):
    v=[net[k].get(d) for d in D]; s=[]; acc=[]
    for i,x in enumerate(v):
        acc.append(x or 0); 
        if len(acc)>N: acc.pop(0)
        s.append(1 if (v[i] is not None and sum(acc)>0) else 0)
    return [0]+s[:-1]     # 收盤後才公布 → 隔天收盤才能動作
base=ev(RF)
fmt=lambda R:' / '.join(f"{x[0]*100:.1f}%" for x in R[:3])+f" | 全段 {R[3][0]*100:.1f}% 回撤 {R[3][1]*100:.0f}% 買進 {R[3][2]} 次"
print('基準 濾網15/4：',fmt(base))
res=[]
for k,N in itertools.product(['外資','投信','合計'],[1,3,5,10,20,40,60,120]):
    s=instsig(k,N)
    for mode in ('單獨','加嚴','放寬'):
        pos=s if mode=='單獨' else [a&b for a,b in zip(RF,s)] if mode=='加嚴' else [a|b for a,b in zip(RF,s)]
        R=ev(pos); win=sum(R[i][0]>base[i][0] for i in range(3))
        res.append((win,R[3][0],k,N,mode,R))
for mode in ('單獨','加嚴','放寬'):
    sub=[x for x in res if x[4]==mode]
    print(f'\n== {mode}：三段都贏基準的組數 {sum(1 for x in sub if x[0]==3)}/{len(sub)}；前 5 名')
    for w,_,k,N,m,R in sorted(sub,key=lambda x:(-x[0],-x[1]))[:5]: print(f'  {k} 近{N}天 贏{w}/3 |',fmt(R))
