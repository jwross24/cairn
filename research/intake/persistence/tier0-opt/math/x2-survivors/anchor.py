R24 = (10 ** 24 - 1) // 9


def rep(n):
    return (10 ** n - 1) // 9


def s_unit(y):
    if y <= 0:
        return None
    e = []
    for p in (2, 3, 7):
        c = 0
        while y % p == 0:
            y //= p
            c += 1
        e.append(c)
    return tuple(e) if y == 1 else None


def pattern_value(nu, eps, digits):
    v = rep(nu)
    for d, e in zip(digits, eps):
        v += (d - 1) * 10 ** e
    return v


def anchor(nu, eps, digits, modulus=R24):
    v = pattern_value(nu, eps, digits)
    y = v % modulus
    if y == 0:
        return None
    f = s_unit(y)
    if f is None:
        return None
    return {"y": y, "abc": f, "kappa": v // modulus}


def half_anchor(nu, eps, digits, jmax=64):
    v = pattern_value(nu, eps, digits)
    for j in range(1, jmax + 1):
        y = (v * pow(2, j)) % R24
        if y == 0:
            continue
        f = s_unit(y)
        if f is not None and f[0] < j:
            return j
    return None


def canon(digits, eps):
    out = []
    i = 0
    n = len(digits)
    while i < n:
        j = i
        while j < n and digits[j] == digits[i]:
            j += 1
        out.extend(sorted(eps[i:j]))
        i = j
    return tuple(out)
