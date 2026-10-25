import os
from math import gcd

MODE = os.environ.get('BRANCHSPLIT', 'on')
MUTANT = os.environ.get('BRANCHSPLIT_MUTANT', '')
COUNTS = {}
AUDIT = os.environ.get('BRANCHSPLIT_AUDIT') is not None
REMOVED = []
TIMES = {}
AUDIT_STRIDE = int(os.environ.get('BRANCHSPLIT_AUDIT_STRIDE', '1'))
AUDIT_CAP = int(os.environ.get('BRANCHSPLIT_AUDIT_CAP', '200000'))

_P10_7 = [pow(10, e, 7) for e in range(6)]
_R7 = [((pow(10, n, 63) - 1) // 9) % 7 for n in range(12)]


def branch_of(D, nu, eps):
    s1 = sum(d - 1 for d in D)
    three_divides = (nu + s1) % 3 == 0
    y7 = _R7[nu % 6]
    for d, e in zip(D, eps):
        y7 += (d - 1) * _P10_7[e % 6]
    seven_divides = y7 % 7 == 0
    return three_divides, seven_divides


def _need(three_divides, seven_divides):
    need_b0 = not three_divides
    need_c0 = not seven_divides
    if MUTANT == 'swap37' and (not three_divides) and seven_divides:
        return False, True
    if MUTANT == 'drop3' and three_divides and not seven_divides:
        return True, True
    return need_b0, need_c0


def coset_meets(co, need_b0, need_c0):
    (b0, c0), (p, q), (r, s) = co.v0, co.u1, co.u2
    if need_b0 and need_c0:
        det = p * s - q * r
        if det == 0:
            return b0 == 0 and c0 == 0
        x_num = -(b0 * s - c0 * r)
        y_num = -(p * c0 - q * b0)
        return x_num % det == 0 and y_num % det == 0
    if need_b0:
        g = gcd(p, r)
        return b0 == 0 if g == 0 else b0 % g == 0
    if need_c0:
        g = gcd(q, s)
        return c0 == 0 if g == 0 else c0 % g == 0
    return True


def keep(D, a, nu, eps, co):
    if MODE == 'off':
        return True
    nb, nc = _need(*branch_of(D, nu, eps))
    return coset_meets(co, nb, nc)


_SEEN = [0]


def note(tag, a, nu, eps, co):
    if not AUDIT:
        return
    if tag == 'c12':
        _SEEN[0] += 1
        if _SEEN[0] % AUDIT_STRIDE:
            return
    if len(REMOVED) < AUDIT_CAP:
        REMOVED.append((tag, a, nu, tuple(eps), tuple(co.v0), tuple(co.u1), tuple(co.u2)))


def filter_list(D, surv, tag):
    before = len(surv)
    out = []
    for t in surv:
        if keep(D, t[0], t[1], t[2], t[3]):
            out.append(t)
        else:
            note(tag, t[0], t[1], t[2], t[3])
    c = COUNTS.setdefault(tag, [0, 0])
    c[0] += before
    c[1] += len(out)
    return out
