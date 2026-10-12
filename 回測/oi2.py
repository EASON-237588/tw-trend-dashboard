import oi
from oi import ev, RF, base, fmt, v, D
def ma(x,N,kind):
    out=[None]*len(x); s=0; q=[]; e=None; a=2/(N+1)
    for i,val in enumerate(x):
        if val is None: continue
        if kind=='一般':
            q.append(val); s+=val
            if len(q)>N: s-=q.pop(0)
            if len(q)==N: out[i]=s/N
        else:
            e=val if e is None else a*val+(1-a)*e; out[i]=e
    return out
print('現行規則：',fmt(base))
rows=[]
for kind in ('一般','加權'):
    for N in [5,8,10,13,15,20,25,30,40,60]:
        m=ma(v,N,kind)
        s=[1 if (v[i] is not None and m[i] is not None and v[i]>m[i]) else 0 for i in range(len(D))]
        for lag in (1,2):
            ss=[0]*lag+s[:-lag]
            for mode in ('單獨','放寬'):
                pos=ss if mode=='單獨' else [a|b for a,b in zip(RF,ss)]
                R=ev(pos); rows.append((kind,N,lag,mode,R))
for mode in ('單獨','放寬'):
    print(f'\n== {mode}（✓＝兩段都贏現行規則；括號＝再晚一天成交）')
    for kind in ('一般','加權'):
        for N in [5,8,10,13,15,20,25,30,40,60]:
            R1=[r for k,n,l,m,r in rows if (k,n,l,m)==(kind,N,1,mode)][0]; R2=[r for k,n,l,m,r in rows if (k,n,l,m)==(kind,N,2,mode)][0]
            ok=lambda R:'✓' if all(R[i][0]>base[i][0] for i in range(2)) else ' '
            print(f"  {kind}{N:2d}天 {ok(R1)} 全段 {R1[2][0]*100:5.1f}% 回撤 {R1[2][1]*100:3.0f}% 交叉買進 {R1[2][2]:3d} 次 ｜晚一天 {ok(R2)} {R2[2][0]*100:5.1f}%")
