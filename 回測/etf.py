from mkt import cfgs, sig, weekly, yrs
from bt import *
import pickle, collections
T=load('TWII','d')
def synth(B,lev,extra):
    out=[dict(B[0])];c=100.0
    for i in range(1,len(B)):
        r=B[i]['c']/B[i-1]['c']-1; c*=1+lev*r+extra/252; out.append(dict(B[i],c=c))
    return out
S={'1倍':synth(T,1,0.03),'2倍':synth(T,2,2*0.03-0.025)}
def wk(B):
    W=weekly(B); last={}
    for b in B: last[dt.date.fromisoformat(b['d']).isocalendar()[:2]]=b['d']
    return [dict(w,d=last[w['k']]) for w in W]
import datetime as dt
TF={'日線':T,'週線':wk(T)}
def idx(B,d): return next(i for i,b in enumerate(B) if b['d']>=d)
def cell(B,pos,a,b,cost=0.0018):
    r=perf(B,pos,a,b,cost);y=yrs(B,a,b);pk=0;bm=0
    for i in range(a,b): pk=max(pk,B[i]['c']);bm=max(bm,1-B[i]['c']/pk)
    cg=lambda x:(1+x)**(1/y)-1
    r.update(bm=bm,cagr=cg(r['ret']),bcagr=cg(r['bh']),cal=cg(r['ret'])/max(r['mdd'],.01),bcal=cg(r['bh'])/max(bm,.01));return r
PER=[('2009-01-01','2017-12-31'),('2018-01-01','2026-12-31'),('2000-01-01','2008-12-31')]
rows=[]
for tf,I in TF.items():
    # 交易序列：把合成價對到 I 的 K 棒（週線取週末收盤）
    for cf in cfgs(tf):
        p=sig(I,cf)
        lim=600 if tf=='日線' else 120
        w=6*cf[1] if cf[0]=='RF' else cf[1]
        if w>lim: continue
        res={}
        for lv,SB in S.items():
            m={b['d']:b['c'] for b in SB}
            B=[dict(b,c=m[b['d']]) for b in I]
            res[lv]=[cell(B,p,idx(B,a),idx(B,b) if b<B[-1]['d'] else len(B)) for a,b in PER]
        rows.append((tf,cf,res))
pickle.dump(rows,open('etf.pkl','wb'))
for lv in S:
  for tf in TF:
    R=[(sum(c['cal']>c['bcal'] for c in r[lv]),sum(c['ret']>c['bh'] for c in r[lv]),cf,r[lv]) for t,cf,r in rows if t==tf]
    print(f"\n=== {lv} {tf}  比值贏(3格)分布",dict(collections.Counter(x[0] for x in R)),'報酬贏分布',dict(collections.Counter(x[1] for x in R)))
    for a,b,cf,cs in sorted(R,key=lambda x:(-x[0],-x[1],-min(c['cal']-c['bcal'] for c in x[3])))[:6]:
        print(f"  {cf} 比值{a}/3 報酬{b}/3 | 年化 "+' '.join(f"{c['cagr']*100:.0f}/{c['bcagr']*100:.0f}" for c in cs)+" | 回撤 "+' '.join(f"{c['mdd']*100:.0f}/{c['bm']*100:.0f}" for c in cs)+f" | 筆數 {cs[0]['n']},{cs[1]['n']},{cs[2]['n']}")
