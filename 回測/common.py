from alletf import L, TM, run, load, calcRF
import alletf
S='2022-05-05'
out=[]
for s,nm in L:
    B=load(s,'d')
    if s=='00631L': B=[b for b in B if b['d']>='2016-01-01']
    if B[0]['d']>'2022-01-01': continue
    a=next(i for i,b in enumerate(B) if b['d']>=S)
    mk=[TM.get(b['d'],0) for b in B]
    out.append((s,nm,run(B,[1]*len(B),a),run(B,mk,a)))
print(f'共同期間 {S} ~ 今天')
print('| 代號 | 類型 | 抱著 年化／回撤 | 看大盤 年化／回撤 |')
for s,nm,h,m in sorted(out,key=lambda x:-x[3][0]):
    print(f"| {s} | {nm} | {h[0]*100:+.1f}% / {h[1]*100:.0f}% | {m[0]*100:+.1f}% / {m[1]*100:.0f}% |")
