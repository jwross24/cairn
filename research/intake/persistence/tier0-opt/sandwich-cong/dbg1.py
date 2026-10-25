import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from congchain import *
b96, _ = load_lam96()
W = Window(b96)
y, a, nu = 1411788, 2, 5
pairs = [(8,0),(8,1),(7,2),(8,5),(8,5)]
print(factor237(y))
groups = rep_groups(pairs)
print(groups)
R96 = (10**96-1)//9
opts = [[None]+ds for e,ds in groups.items()]
es = list(groups.keys())
yp = y >> a
M2 = 480 - a
for ch in itertools.product(*opts):
    X = R96 + sum((d-1)*10**e for d,e in zip(ch,es) if d)
    if X % (1<<(a+1)) != (1<<a) or X % 5 == 0:
        continue
    u2 = (X >> a) * pow(yp, -1, 1<<M2) % (1<<M2)
    u5 = X * pow(y, -1, 5**480) % 5**480
    f2 = W.full_member2(u2) if True else None
    # reduce full to modulus 2^M2 consistent
    f5 = W.full_member5(u5)
    # formula
    w = wrap_of(y, nu, pairs)
    S_all = sum((d-1)*10**e for d,e in pairs)
    T = 10**nu + 9*S_all + w
    SF = sum((d-1)*10**e for d,e in zip(ch,es) if d)
    form = ((9*SF - T) % (2**(a+9)*5**5) == 0)
    print(ch, f2, f5, form)
