from bt import load, calcRF
L=[('0050','市值'),('006208','市值'),('0051','中型100'),('0052','科技'),('0053','電子'),('0055','金融'),('00692','公司治理'),('00850','ESG'),('00881','5G'),
   ('0056','高股息'),('00713','高息低波'),('00878','ESG高息'),('00900','特選高息'),('00919','精選高息'),('00929','科技優息'),('00939','高息動能'),('00940','價值高息'),('00891','半導體'),
   ('00631L','正2'),('00663L','加權正2'),('00675L','加權正2'),('00685L','加權正2')]
T=load('TWII','d'); tp=calcRF(T,15,4,useVol=False)[0]; TM={b['d']:tp[i] for i,b in enumerate(T)}
COST=0.0018
def run(B,pos,a):
    eq=pk=1;mdd=0;p=0;n=0
    for i in range(a,len(B)):
        if i>a: eq*=1+p*(B[i]['c']/B[i-1]['c']-1)
        np_=1 if pos[i]==1 else 0
        if np_!=p: eq*=1-COST/2; n+=np_>p; p=np_
        pk=max(pk,eq); mdd=max(mdd,1-eq/pk)
    y=(B[-1]['t']-B[a]['t'])/365.25/86400
    return eq**(1/y)-1, mdd, n
rows=[]
for s,nm in L:
    B=load(s,'d')
    if s=='00631L': B=[b for b in B if b['d']>='2016-01-01']
    a=90
    own=calcRF(B,15,4,useVol=False)[0]; mk=[TM.get(b['d'],0) for b in B]
    hold=run(B,[1]*len(B),a); m=run(B,mk,a); o=run(B,own,a)
    y=(B[-1]['t']-B[a]['t'])/365.25/86400
    rows.append((s,nm,B[a]['d'],y,hold,m,o))
print('| 代號 | 類型 | 起算 | 年數 | 抱著 年化／回撤 | 看大盤 年化／回撤／買進次數 | 看自己 年化／回撤／買進次數 |')
for s,nm,d,y,h,m,o in rows:
    f=lambda r,k=False:f"{r[0]*100:+.1f}% / {r[1]*100:.0f}%"+(f" / {r[2]}" if k else "")
    print(f"| {s} | {nm} | {d} | {y:.1f} | {f(h)} | {f(m,1)} | {f(o,1)} |")
import pickle; pickle.dump(rows,open('alletf.pkl','wb'))
