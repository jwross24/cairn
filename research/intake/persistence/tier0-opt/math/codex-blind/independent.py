from collections import Counter, defaultdict
from math import gcd


def branch_keep(digits, nu, eps, origin, basis):
    r3 = (nu + sum(d - 1 for d in digits)) % 3
    r7 = ((10 ** (nu % 6) - 1) // 9 + sum(
        (d - 1) * pow(10, e % 6, 7) for d, e in zip(digits, eps)
    )) % 7
    b, c = origin
    u, v = basis
    if r3 and r7:
        det = u[0] * v[1] - u[1] * v[0]
        return (b * v[1] - c * v[0]) % det == 0 and (
            u[0] * c - u[1] * b
        ) % det == 0
    if r3 and b % gcd(u[0], v[0]):
        return False
    if r7 and c % gcd(u[1], v[1]):
        return False
    return True


def level12_origin(digits, nu, eps, a, pdata, solver):
    logs = []
    for pd in pdata:
        value = (pd.R[nu] + sum(
            (d - 1) * pd.pow10[e] for d, e in zip(digits, eps)
        )) % pd.p
        if not value:
            return None
        logs.append(pd.log(value))
    point = solver.solve(logs)
    if point is None or (a - point[0]) % solver.g:
        return None
    shift = (a - point[0]) // solver.g
    return (point[1] + shift * solver.u[1], point[2] + shift * solver.u[2])


def depth1_count(a, target, digit_positions, maxstates=1_000_000):
    width = a + 9
    if not 0 <= a <= 87:
        raise ValueError("depth-1 formula requires 0 <= a <= 87")
    masks = defaultdict(Counter)
    for digit, position in digit_positions:
        if not 2 <= digit <= 9 or not 0 <= position < 96:
            raise ValueError((digit, position))
        masks[position][digit] += 1
    modulus = 3125 * 2 ** width
    states = {target % modulus: 1}
    for position in range(width):
        following = defaultdict(int)
        next_modulus = modulus >> (position + 1)
        scale = 5 ** position
        choices = [(1, 1), *masks[position].items()]
        for residual, multiplicity in states.items():
            for digit, occurrences in choices:
                difference = residual - digit * scale
                if difference % 2:
                    continue
                next_residual = (difference // 2) % next_modulus
                if position == 4 and next_residual % 3125:
                    continue
                following[next_residual] += multiplicity * occurrences
        if len(following) > maxstates:
            raise RuntimeError("independent automaton state budget exceeded")
        states = following
        if not states:
            return 0
    count = states.get(0, 0)
    for position, counts in masks.items():
        if position >= width:
            count *= 1 + sum(counts.values())
    return count
