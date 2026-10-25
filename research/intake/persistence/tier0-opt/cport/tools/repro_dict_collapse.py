#!/usr/bin/env python3
"""Exit 0 iff tier0/deepcut.py's stage-2 bookkeeping (verbatim `fixed = dict(...)`, `free = [...]`) builds a tail L
that excludes a genuine S-unit's own point while the per-item bookkeeping keeps it.
Run: uv run --no-project --with sympy --with gmpy2 python repro_dict_collapse.py
Reads tier0 only (imports deepcut, lattice, descent from it); writes nothing."""
import os, sys
T = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
os.chdir(T); sys.path.insert(0, T)
import deepcut as DC
from lattice import Coset
from descent import cut_coset, v2

LMAX = 96
Lam = DC.kernel_lattice()
RK = (10 ** 192 - 1) // 9

def items_of(y, nprefix=2 * LMAX):
    out = []
    for p in range(nprefix):
        d = (y // 10 ** p) % 10
        if d != 1: out.append((d, p % LMAX, p // LMAX))
    return out

found = None
for a in range(0, 12):
    for b in range(0, 400):
        c = 400 - b // 2
        y = 2 ** a * 3 ** b * 7 ** c
        if len(str(y)) < 300: continue
        its = items_of(y)
        keys = [(d, e) for d, e, t in its]
        dups = sorted({k for k in keys if keys.count(k) > 1})
        if dups:
            found = (a, b, c, y, its, dups); break
    if found: break
a, b, c, y, its, dups = found
print(f"genuine S-unit y' = 2^{a} 3^{b} 7^{c}, {len(str(y))} digits; repeated (d, e) pairs in its lowest 192 digits: {dups[:3]}")

co = Coset((b, c), Lam.u1, Lam.u2)
De = [(d, e) for d, e, t in its]

L1 = (10 ** 96 - 1) // 9 + sum((d - 1) * 10 ** e for d, e, t in its if t == 0)
assert L1 == y % 10 ** 96 and v2(L1) == a
co1 = cut_coset(co, a, L1, 96)
assert co1 is not None and co1.contains(b, c), "depth 1 must keep the genuine point"

assigned = tuple((d, e, 0) for d, e, t in its if t == 0)
fixed = dict(((d, e), t) for d, e, t in assigned)
free = [(d, e) for d, e in De if (d, e) not in fixed]
L_py = RK
for (d, e), t in fixed.items(): L_py += (d - 1) * 10 ** (e + LMAX * t)
for (d, e) in free:
    L_py += (d - 1) * 10 ** (e + LMAX * 1)

L_true = RK + sum((d - 1) * 10 ** (e + LMAX * t) for d, e, t in its)
assert L_true == y % 10 ** 192

co_true = cut_coset(co1, a, L_true, 192)
kept_sound = co_true is not None and co_true.contains(b, c)
co_py = cut_coset(co1, a, L_py, 192) if v2(L_py) == a else None
kept_py = co_py is not None and co_py.contains(b, c)
print(f"L_python != y' mod 10^192: {L_py != L_true}; v2(L_python) == a: {v2(L_py) == a}")
print(f"stage-2 cut keeps the genuine point: per-item bookkeeping {kept_sound}, Python dict bookkeeping {kept_py}")
sys.exit(0 if (kept_sound and not kept_py and L_py != L_true) else 1)
