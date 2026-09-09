"""Affine short-Weierstrass arithmetic over GMP integers and a baby-step giant-step search
for the group order inside the Hasse interval.

gmpy2 is the only import, so nothing here reaches libpari and an order this module recovers
is independent evidence against the same curve's PARI-counted order.
"""

from gmpy2 import invert, isqrt, mpz


class NotOnCurve(ValueError):
    pass


class OrderAmbiguous(ValueError):
    def __init__(self, candidates):
        candidates = tuple(candidates)
        super().__init__(f"no single order in the Hasse interval fits every point: {[int(m) for m in candidates]}")
        self.candidates = candidates


def is_on_curve(p, a, b, point):
    if point is None:
        return True
    p, a, b = mpz(p), mpz(a), mpz(b)
    x, y = mpz(point[0]), mpz(point[1])
    return 0 <= x < p and 0 <= y < p and (y * y - (x * x * x + a * x + b)) % p == 0


def require_on_curve(p, a, b, point, name):
    if point is None or not is_on_curve(p, a, b, point):
        raise NotOnCurve(f"{name} = {point} is not an affine point on y^2 = x^3 + {a}x + {b} over F_{p}")
    return mpz(point[0]), mpz(point[1])


def neg(p, point):
    if point is None:
        return None
    x, y = point
    return mpz(x), (-mpz(y)) % mpz(p)


def double(p, a, point):
    if point is None:
        return None
    x, y = point
    if y == 0:
        return None
    slope = (3 * x * x + a) * invert(2 * y, p) % p
    x3 = (slope * slope - 2 * x) % p
    return x3, (slope * (x - x3) - y) % p


def add(p, a, left, right):
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None
        return double(p, a, left)
    slope = (y2 - y1) * invert(x2 - x1, p) % p
    x3 = (slope * slope - x1 - x2) % p
    return x3, (slope * (x1 - x3) - y1) % p


def sub(p, a, left, right):
    return add(p, a, left, neg(p, right))


def mul(p, a, point, k):
    k = mpz(k)
    if k < 0:
        return mul(p, a, neg(p, point), -k)
    result = None
    for bit in f"{int(k):b}":
        result = double(p, a, result)
        if bit == "1":
            result = add(p, a, result, point)
    return result


def hasse_interval(p):
    p = mpz(p)
    bound = isqrt(4 * p)
    return p + 1 - bound, p + 1 + bound


def search_width(p):
    lo, hi = hasse_interval(p)
    return isqrt(hi - lo) + 1


def orders_in_hasse(p, a, b, point):
    p, a, b = mpz(p), mpz(a), mpz(b)
    point = require_on_curve(p, a, b, point, "P")
    lo, hi = hasse_interval(p)
    width = search_width(p)
    table = {}
    baby = None
    minus = neg(p, point)
    for k in range(int(width)):
        table.setdefault(baby, []).append(mpz(k))
        baby = add(p, a, baby, minus)
    giant = mul(p, a, point, lo)
    stride = mul(p, a, point, width)
    found = set()
    for i in range(int((hi - lo) // width) + 1):
        for k in table.get(giant, ()):
            m = lo + i * width + k
            if 0 < m <= hi:
                found.add(m)
        giant = add(p, a, giant, stride)
    return tuple(sorted(found))


def group_order(p, a, b, points):
    candidates = None
    for point in points:
        found = set(orders_in_hasse(p, a, b, point))
        candidates = found if candidates is None else candidates & found
        if candidates is not None and len(candidates) == 1:
            return next(iter(candidates))
    raise OrderAmbiguous(sorted(() if candidates is None else candidates))
