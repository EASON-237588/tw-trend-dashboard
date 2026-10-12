import bt
L=['0050','006208','0051','0052','0053','0055','00692','00850','00881','0056','00713','00878','00900','00919','00929','00939','00940','00891','00631L','00663L','00675L','00685L']
LEV={'00631L','00663L','00675L','00685L'}
def yr(B):
    o={}
    for b in B: o.setdefault(b['d'][:4],[b['c'],b['c']]); o[b['d'][:4]][1]=b['c']
    return {y:v[1]/v[0]-1 for y,v in o.items()}
T=yr(bt.load('TWII','d'))
for s in L:
    bt.LOG.clear()
    src=open('bt.py',encoding='utf-8').read()
    B=bt.load(s,'d') if s not in LEV else None
    if s in LEV:
        import json
        B=bt.load(s,'d')  # 已用 0.105 門檻 → 重做
    ev=list(bt.LOG)
    Y=yr(B); lev=2 if s in LEV else 1
    bad=[f"{y}:{Y[y]*100:+.0f}/{T[y]*lev*100:+.0f}" for y in sorted(Y) if abs(Y[y]-lev*T[y])>0.25*lev]
    print(f"{s:7s} 起{B[0]['d']} 修正{len(ev)}次 {[e[1] for e in ev][:5]} 偏離大的年份(ETF/指數x槓桿):{bad}")
