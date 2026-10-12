from bt import *
from mkt import sig
import itertools, pickle, sys, datetime as dt
T=load('TWII','d')
# 每日資產報酬：正2、反1、0050型
r=[0]+[T[i]['c']/T[i-1]['c']-1 for i in range(1,len(T))]
A={'2':[0]+[2*x+(2*0.03-0.025)/252 for x in r[1:]],'-1':[0]+[-x-(0.03+0.01)/252 for x in r[1:]],'1':[0]+[x+0.03/252 for x in r[1:]]}
def chunk(B,n):
    out=[]
    for k in range(0,len(B)-n+1,n) if n>1 else range(len(B)):
        g=B[k:k+n] if n>1 else [B[k]]
        out.append(dict(t=g[-1]['t'],d=g[-1]['d'],o=g[0]['o'],h=max(x['h'] for x in g),l=min(x['l'] for x in g),c=g[-1]['c'],v=sum(x['v'] for x in g),e=(k+n-1) if n>1 else k))
    return out
SEG=[('2000-01-01','2008-12-31'),('2009-01-01','2017-12-31'),('2018-01-01','2026-12-31'),('2000-01-01','2026-12-31')]
def run(I,pos,bear,lag=0,cost=0.0018):
    """I 的 e = 對應日線索引；回傳各段 年化、回撤、筆數"""
    if lag: pos=[0]*lag+pos[:-lag]
    # 逐日：第 k 根收盤決定的部位，套用到下一根之間的每一天
    n=len(T);dp=[0]*n
    for k in range(len(I)-1):
        for j in range(I[k]['e']+1,I[k+1]['e']+1): dp[j]=pos[k]
    out=[]
    for a,b in SEG:
        ia=next(i for i,x in enumerate(T) if x['d']>=a); ib=max(i for i,x in enumerate(T) if x['d']<=b)
        eq=pk=1;mdd=0;tr=0;prev=dp[ia]
        for j in range(ia+1,ib+1):
            p=dp[j]
            if p!=prev: eq*=1-cost/2*(abs(p-prev) if bear=='-1' else abs((p>0)-(prev>0)));tr+=p!=prev
            prev=p
            ret=A['2'][j] if p>0 else (A['-1'][j] if (p<0 and bear=='-1') else 0)
            eq*=1+ret;pk=max(pk,eq);mdd=max(mdd,1-eq/pk)
        y=(T[ib]['t']-T[ia]['t'])/365.25/86400
        out.append((eq**(1/y)-1,mdd,tr))
    return out
BH=[]
for a,b in SEG:
    ia=next(i for i,x in enumerate(T) if x['d']>=a); ib=max(i for i,x in enumerate(T) if x['d']<=b)
    e=1
    for j in range(ia+1,ib+1): e*=1+A['1'][j]
    BH.append(e**(1/((T[ib]['t']-T[ia]['t'])/365.25/86400))-1)
CF=[('RF',p,m) for p,m in itertools.product([3,5,8,10,12,15,20,25,30,40,50,65,80,100,120],[0.5,1,1.5,2,2.5,3,3.5,4,5,6,7.5,9,11,13])]
CF+=[('Don',l,s) for l,s in itertools.product([3,5,8,10,15,20,30,50,80,120],[0,5])]+[('MA',n,0) for n in [3,5,8,10,15,20,30,40,60,80,100,150,200]]
if __name__=='__main__':
    rows=[]
    for n,tf in [(1,'日線'),(2,'2日'),(3,'3日'),(5,'5日')]:
        I=chunk(T,n)
        for cf in CF:
            w=6*cf[1] if cf[0]=='RF' else cf[1]
            if w*n>600: continue
            mode='both' if True else 'long'
            p=calcRF(I,cf[1],cf[2],useVol=False)[0] if cf[0]=='RF' else (calcDon(I,cf[1],'both',0)[0] if cf[0]=='Don' else None)
            if cf[0]=='MA':
                m=sma([b['c'] for b in I],cf[1]); p=[(1 if I[i]['c']>m[i] else -1) if m[i] else 0 for i in range(len(I))]
            for bear in ('0','-1'):
                rows.append((tf,cf,bear,run(I,p,bear),run(I,p,bear,1)))
        print(tf,'done',file=sys.stderr)
    pickle.dump((rows,BH),open('big.pkl','wb'))
