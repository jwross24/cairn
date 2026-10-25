import re, math, itertools
from math import comb, log10
F='/Users/jwross/Documents/cairn/research/intake/persistence/tier0/FRONTIER.md'
rows=[]
for l in open(F):
    m=re.match(r'\| (A|B|C) \| (A_\d) \| (\d+) \| 2\^(\d+)·3\^(\d+)·7\^(\d+) \| ([\d.e+]+) \| (\d+) \| (\d+) \|',l)
    if m:
        rows.append((m.group(1),int(m.group(3)),(int(m.group(4)),int(m.group(5)),int(m.group(6))),float(m.group(7)),int(m.group(8)),int(m.group(9))))
DIG={2:(1,0,0),3:(0,1,0),4:(2,0,0),6:(1,1,0),7:(0,0,1),8:(3,0,0),9:(0,2,0)}
def multisets(e):
    A,B,C=e
    out=[]
    m7=C
    # counts m2,m3,m4,m6,m8,m9 with 2-exp=A, 3-exp=B
    for m8 in range(A//3+1):
      for m4 in range((A-3*m8)//2+1):
        for m6 in range(min(B,A-3*m8-2*m4)+1):
          m2=A-3*m8-2*m4-m6
          if m2<0: continue
          for m9 in range((B-m6)//2+1):
            m3=B-m6-2*m9
            if m3<0: continue
            out.append({2:m2,3:m3,4:m4,6:m6,7:m7,8:m8,9:m9})
    return out
def N(M,L):
    r=L
    for d,m in M.items(): r*=comb(L-1+m,m)
    return r
I96=43494223306982419262991237120000
G96=10**93.588; H37=10**56.449
res=[]
for tier,s,e,n12,kmax,nms in rows:
    if tier=='A': continue
    ms=multisets(e)
    n12c=sum(N(M,12) for M in ms); n96=sum(N(M,96) for M in ms)
    kk=max(sum(M.values()) for M in ms)
    d96=lambda Ap: H37*(Ap+1)/G96
    # A unknown: bracket 20..150
    lo=n96*d96(20); hi=n96*d96(150)
    print(f"{tier} s={s} kmax={kk} (tab {kmax}) #M={len(ms)} (tab {nms}) N12={n12c:.3e} (tab {n12:.3e}) N96={n96:.3e} E96rand={lo:.2e}..{hi:.2e}  forecast open@96~{1e-8*n12:.1e}")
