"""Affine short-Weierstrass arithmetic over F_p in plain Python integers.

The identity is None. Every function is a pure function of its arguments, so a
walk built on it is deterministic and a second implementation (libpari through
cairn.pari) can disagree with it, which is what makes the two independent.
"""


class NotOnCurve(ValueError):
    pass


def is_on_curve(p, a, b, point):
    if point is None:
        return True
    x, y = point
    return 0 <= x < p and 0 <= y < p and (y * y - (x * x * x + a * x + b)) % p == 0


def neg(p, point):
    if point is None:
        return None
    x, y = point
    return (x, (-y) % p)


def double(p, a, point):
    if point is None:
        return None
    x, y = point
    if y == 0:
        return None
    slope = (3 * x * x + a) * pow(2 * y, -1, p) % p
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
    slope = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (slope * slope - x1 - x2) % p
    return x3, (slope * (x1 - x3) - y1) % p


def sub(p, a, left, right):
    return add(p, a, left, neg(p, right))


def mul(p, a, point, k):
    if k < 0:
        return mul(p, a, neg(p, point), -k)
    result = None
    for bit in f"{k:b}":
        result = double(p, a, result)
        if bit == "1":
            result = add(p, a, result, point)
    return result


def mul_ops(k):
    k = abs(k)
    if k == 0:
        return 0
    return (k.bit_length() - 1) + (k.bit_count() - 1)


def canonical(p, point):
    """The representative of {X, -X} with the smaller y, and whether X was negated."""
    if point is None:
        return None, False
    x, y = point
    if y > p - y:
        return (x, p - y), True
    return point, False


def require_on_curve(p, a, b, point, name):
    if point is None or not is_on_curve(p, a, b, point):
        raise NotOnCurve(f"{name} = {point} is not an affine point on y^2 = x^3 + {a}x + {b} over F_{p}")
    return point
