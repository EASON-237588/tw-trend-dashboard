import json, itertools
from bt import load, calcRF, sma
T=load('TWII','d'); D=[b['d'] for b in T]
RF=[1 if p==1 else 0 for p in calcRF(T,15,4,useVol=False)[0]]
net={x['date']:x['long_open_interest_balance_volume']-x['short_open_interest_balance_volume'] for x in json.load(open('txoi.json')) if x['institutional_investors']=='外資'}
r=[0]+[T[i]['c']/T[i-1]['c']-1 for i in range(1,len(T))]; R2=[0]+[2*x+0.035/252 for x in r[1:]]
SEG=[('2018-07-01','2022-06-30'),('2022-07-01','2026-12-31'),('2018-07-01','2026-12-31')]
def ev(pos,cost=0.0018):
    out=[]
    for a,b in SEG:
        ia=next(i for i,d in enumerate(D) if d>=a); ib=max(i for i,d in enumerate(D) if d<=b)
        eq=pk=1;mdd=0;n=0
        for j in range(ia+1,ib+1):
            p,pp=pos[j-1],pos[j-2]
            if p!=pp: eq*=1-cost/2; n+=p>pp
            eq*=1+(R2[j] if p else 0); pk=max(pk,eq); mdd=max(mdd,1-eq/pk)
        out.append((eq**(252/(ib-ia))-1,mdd,n))
    return out
# 外資淨部位序列（缺值沿用前一天）
v=[];last=None
for d in D: last=net.get(d,last); v.append(last)
def sig(kind,N):
    s=[]
    m=sma([x or 0 for x in v],N)
    for i in range(len(D)):
        if v[i] is None or i<N or v[i-N] is None: s.append(0); continue
        if kind=='加碼': s.append(1 if v[i]-v[i-N]>0 else 0)
        elif kind=='高於均': s.append(1 if v[i]>m[i] else 0)
    return [0]+s[:-1]   # 收盤後公布 → 隔天收盤動作
fmt=lambda R:f"{R[0][0]*100:5.1f}% / {R[1][0]*100:5.1f}% | 全段 {R[2][0]*100:5.1f}% 回撤 {R[2][1]*100:3.0f}% 買進 {R[2][2]:3d} 次"
base=ev(RF); hold=ev([1]*len(D))
print('正2抱著   ：',fmt(hold)); print('現行規則  ：',fmt(base))
res=[]
for kind,N in itertools.product(['加碼','高於均'],[1,3,5,10,20,40,60]):
    s=sig(kind,N)
    for mode in ('單獨','加嚴','放寬'):
        pos=s if mode=='單獨' else [a&b for a,b in zip(RF,s)] if mode=='加嚴' else [a|b for a,b in zip(RF,s)]
        R=ev(pos); res.append((sum(R[i][0]>base[i][0] for i in range(2)),R[2][0],kind,N,mode,R))
for mode in ('單獨','加嚴','放寬'):
    sub=[x for x in res if x[4]==mode]
    print(f"\n== {mode}：兩段都贏現行規則 {sum(1 for x in sub if x[0]==2)}/{len(sub)}")
    for w,_,k,N,m,R in sorted(sub,key=lambda x:(-x[0],-x[1]))[:5]: print(f"  {k} {N:2d}天 贏{w}/2 |",fmt(R))

print('\n== 放寬＋加碼，相鄰天數（兩段 / 全段 / 回撤）')
for N in [5,8,10,12,15,18,20,22,25,30,35,40,50,60]:
    s=sig('加碼',N); R=ev([a|b for a,b in zip(RF,s)]); print(f"  {N:2d}天 {fmt(R)}  {'✓' if all(R[i][0]>base[i][0] for i in range(2)) else ''}")
print('\n== 再晚一天成交')
for N in [15,20,25]:
    s=sig('加碼',N); s=[0]+s[:-1]; R=ev([a|b for a,b in zip(RF,s)]); print(f"  {N}天 {fmt(R)}")
print('\n== 逐年（年報酬：現行規則 / 放寬加碼20天 / 正2抱著）')
s=sig('加碼',20); P=[a|b for a,b in zip(RF,s)]
for y in range(2018,2027):
    ia=next(i for i,d in enumerate(D) if d>=f'{y}-01-01' and d>='2018-07-01'); ib=max(i for i,d in enumerate(D) if d<=f'{y}-12-31')
    def yr(pos):
        e=1
        for j in range(ia+1,ib+1):
            if pos[j-1]!=pos[j-2]: e*=1-0.0009
            e*=1+(R2[j] if pos[j-1] else 0)
        return e-1
    print(f"  {y}  {yr(RF)*100:+6.1f}%  {yr(P)*100:+6.1f}%  {yr([1]*len(D))*100:+6.1f}%")
