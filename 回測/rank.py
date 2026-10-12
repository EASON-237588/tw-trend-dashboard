import pickle, collections
rows,BH=pickle.load(open('big.pkl','rb'))
print('0050抱著 年化 2000-08 / 09-17 / 18-26 / 全段:',' '.join(f"{x*100:.1f}%" for x in BH))
ok=lambda r:all(r[i][0]>BH[i] for i in range(3))
D={(t,cf,b):(r0,r1) for t,cf,b,r0,r1 in rows}
def nb(t,cf,b):
    if cf[0]!='RF': return None
    P=[3,5,8,10,12,15,20,25,30,40,50,65,80,100,120];M=[0.5,1,1.5,2,2.5,3,3.5,4,5,6,7.5,9,11,13]
    i,j=P.index(cf[1]),M.index(cf[2]);v=[]
    for di in (-1,0,1):
        for dj in (-1,0,1):
            if 0<=i+di<len(P) and 0<=j+dj<len(M) and (t,('RF',P[i+di],M[j+dj]),b) in D: v.append(D[(t,('RF',P[i+di],M[j+dj]),b)][1][3][0])
    return sum(v)/len(v)
for b in ('0','-1'):
    print('\n######## 空方時', '空手' if b=='0' else '持有反1')
    for t in ('日線','2日','3日','5日'):
        R=[(t2,cf,r0,r1) for t2,cf,b2,r0,r1 in rows if t2==t and b2==b]
        P=[x for x in R if ok(x[2]) and ok(x[3])]
        print(f"== {t}  合格 {len(P)}/{len(R)}")
        for t2,cf,r0,r1 in sorted(P,key=lambda x:-x[3][3][0])[:5]:
            n=nb(t,cf,b)
            print(f"   {cf} 全段年化 {r0[3][0]*100:.1f}%（晚一根 {r1[3][0]*100:.1f}%）周圍平均 {n*100 if n else 0:.1f}% | 三段 "+' / '.join(f"{r0[i][0]*100:.0f}%" for i in range(3))+f" | 回撤 {r0[3][1]*100:.0f}% | 29年買賣 {r0[3][2]} 次")
