import oi
from oi import ev, RF, base, v, D
def hyst(N,K):
    st=0; out=[]
    for i in range(len(D)):
        if i>=N and v[i] is not None and v[i-N] is not None:
            c=v[i]-v[i-N]
            if c>K: st=1
            elif c<-K: st=0
        out.append(st)
    return out
def flips(s,a='2025-09-08'):
    i0=next(i for i,d in enumerate(D) if d>=a); return sum(1 for i in range(i0+1,len(s)) if s[i]!=s[i-1])
print('現行規則：全段 %.1f%% 回撤 %.0f%%' % (base[2][0]*100, base[2][1]*100))
print('天數 門檻(口) | 兩段 / 全段 / 回撤 | 晚一天全段 | 8 年翻轉次數 | 近 13 個月交叉')
for N in (15,20,25):
    for K in (0,500,1000,2000,3000,5000,8000,12000,20000):
        s=hyst(N,K); s1=[0]+s[:-1]; s2=[0,0]+s[:-2]
        R=ev([a|b for a,b in zip(RF,s1)]); R2=ev([a|b for a,b in zip(RF,s2)])
        ok='✓' if all(R[i][0]>base[i][0] for i in range(2)) and R2[2][0]>base[2][0] else ' '
        print(f"{N:3d}天 {K:6d} {ok} | {R[0][0]*100:5.1f}% / {R[1][0]*100:5.1f}% / {R[2][0]*100:5.1f}% / {R[2][1]*100:3.0f}% | {R2[2][0]*100:5.1f}% | {sum(1 for i in range(1,len(s)) if s[i]!=s[i-1]):4d} | {flips(s):3d}")
    print()
