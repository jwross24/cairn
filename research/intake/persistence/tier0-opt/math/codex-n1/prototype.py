import argparse
from datetime import datetime
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
from math import gcd, isqrt
from pathlib import Path
from random import Random
import sys
from time import monotonic
from zoneinfo import ZoneInfo


def clock_guard():
    now = datetime.now(ZoneInfo("America/New_York"))
    minute = now.hour * 60 + now.minute
    if 105 <= minute < 330:
        raise RuntimeError("Computation forbidden from 01:45 through 05:29 EDT")
    return now.isoformat()


def valuation(n, p):
    if not n:
        raise ValueError("valuation of zero")
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    return v


def principal_log(u, p, precision):
    modulus = p**precision
    x = (u - 1) % modulus
    if not x:
        return 0
    assert x % (4 if p == 2 else p) == 0
    result = 0
    for k in range(1, 2 * precision + 1):
        v = valuation(k, p)
        divisor = p**v
        term = pow(x, k, modulus * divisor) // divisor
        term = term * pow(k // divisor, -1, modulus) % modulus
        result += term if k % 2 else -term
    return result % modulus


def log2_unit(u, precision):
    sign = 1 if u % 4 == 1 else -1
    return principal_log(sign * u, 2, precision)


def log5_unit(u, precision):
    modulus = 5**precision
    return principal_log(pow(u, 4, modulus), 5, precision) * pow(4, -1, modulus) % modulus


def target_rows(base, deltas, a, precision, parent=None):
    assert precision >= a + 3
    assert valuation(base, 2) == a and base % 5
    n2 = precision - a
    u0 = base // 2**a
    h = max(a + 2, (precision + a + 1) // 2)
    assert all(d % 10**h == 0 for d in deltas)
    r = len(deltas)
    c2 = []
    c5 = []
    for delta in deltas:
        normalized = delta // 2**a
        ratio2 = 1 + normalized * pow(u0, -1, 2**n2)
        ratio5 = 1 + normalized * pow(u0, -1, 5**precision)
        c2.append(principal_log(ratio2, 2, n2) // 4)
        c5.append(principal_log(ratio5, 5, precision) // 5)
    rows = [
        ([0] * r + [1, 1], 0 if u0 % 4 == 1 else 1, 2),
        ([0] * r + [3, 1], {1: 0, 2: 1, 4: 2, 3: 3}[u0 % 5], 4),
        ([-c for c in c2] + [log2_unit(3, n2) // 4, log2_unit(7, n2) // 4], log2_unit(u0, n2) // 4, 2 ** (n2 - 2)),
        ([-c for c in c5] + [log5_unit(3, precision) // 5, log5_unit(7, precision) // 5], log5_unit(u0, precision) // 5, 5 ** (precision - 1)),
    ]
    if parent is not None:
        point, u, v = parent
        det = u[0] * v[1] - u[1] * v[0]
        assert det
        rows.extend([
            ([0] * r + [v[1], -v[0]], v[1] * point[0] - v[0] * point[1], abs(det)),
            ([0] * r + [-u[1], u[0]], -u[1] * point[0] + u[0] * point[1], abs(det)),
        ])
    return rows


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def extended_gcd(a, b):
    r0, r1, s0, s1, t0, t1 = a, b, 1, 0, 0, 1
    while r1:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        s0, s1 = s1, s0 - q * s1
        t0, t1 = t1, t0 - q * t1
    if r0 < 0:
        return -r0, -s0, -t0
    return r0, s0, t0


def affine_lattice(rows, n):
    point = [0] * n
    basis = [[int(i == j) for i in range(n)] for j in range(n)]
    for coefficients, target, modulus in rows:
        clock_guard()
        values = [dot(coefficients, col) for col in basis]
        rhs = (target - dot(coefficients, point)) % modulus
        for j in range(1, n):
            if not values[j]:
                continue
            a, b = values[0], values[j]
            d, s, t = extended_gcd(a, b)
            first, other = basis[0], basis[j]
            basis[0] = [s * x + t * y for x, y in zip(first, other)]
            basis[j] = [-b // d * x + a // d * y for x, y in zip(first, other)]
            values[0], values[j] = d, 0
        g = values[0]
        if not g:
            if rhs:
                return None
            continue
        d = gcd(g, modulus)
        if rhs % d:
            return None
        period = modulus // d
        offset = rhs // d * pow(g // d, -1, period) % period if period > 1 else 0
        point = [x + offset * y for x, y in zip(point, basis[0])]
        basis[0] = [period * x for x in basis[0]]
    assert all((dot(row, point) - value) % mod == 0 for row, value, mod in rows)
    assert all(dot(row, col) % mod == 0 for row, _, mod in rows for col in basis)
    return point, basis


def gram_schmidt(basis):
    stars, norms, mu = [], [], []
    for i, vector in enumerate(basis):
        row = [F(0)] * len(basis)
        star = list(map(F, vector))
        for j in range(i):
            row[j] = dot(vector, stars[j]) / norms[j]
            star = [x - row[j] * y for x, y in zip(star, stars[j])]
        stars.append(star)
        norms.append(dot(star, star))
        mu.append(row)
    assert all(norm > 0 for norm in norms)
    return stars, norms, mu


def nearest_integer(x):
    return (x + F(1, 2)).__floor__()


def reduce_basis(basis):
    basis = [list(map(F, vector)) for vector in basis]
    k = 1
    steps = 0
    while k < len(basis):
        clock_guard()
        steps += 1
        _, norms, mu = gram_schmidt(basis)
        for j in range(k - 1, -1, -1):
            q = nearest_integer(mu[k][j])
            if q:
                basis[k] = [x - q * y for x, y in zip(basis[k], basis[j])]
                _, norms, mu = gram_schmidt(basis)
        if norms[k] >= (F(3, 4) - mu[k][k - 1] ** 2) * norms[k - 1]:
            k += 1
        else:
            basis[k], basis[k - 1] = basis[k - 1], basis[k]
            k = max(1, k - 1)
    return basis, steps


class BudgetExceeded(Exception):
    pass


def sphere_points(basis, target, radius2, stats, budget):
    stars, norms, mu = gram_schmidt(basis)
    coordinates = [dot(target, star) / norm for star, norm in zip(stars, norms)]
    n = len(basis)
    selected = [0] * n

    def recurse(i, remaining):
        clock_guard()
        stats["nodes"] += 1
        if stats["nodes"] > budget:
            raise BudgetExceeded
        if i < 0:
            stats["sphere_points"] += 1
            yield [sum(selected[j] * basis[j][k] for j in range(n)) for k in range(n)]
            return
        center = coordinates[i] - sum(selected[j] * mu[j][i] for j in range(i + 1, n))
        quotient = remaining / norms[i]
        span = isqrt(quotient.numerator // quotient.denominator) + 1
        floor = center.__floor__()
        choices = range(floor - span, floor + span + 2)
        for value in sorted(choices, key=lambda z: abs(z - center)):
            expense = norms[i] * (value - center) ** 2
            if expense <= remaining:
                selected[i] = value
                yield from recurse(i - 1, remaining - expense)

    yield from recurse(n - 1, F(radius2))


def box_solve(rows, r, bound, groups=(), budget=200000, alphabets=None):
    assert bound >= 0
    stats = {"nodes": 0, "sphere_points": 0, "lll_steps": 0, "complete": True}
    lattice = affine_lattice(rows, r + 2)
    if lattice is None:
        return set(), stats
    point, basis = lattice
    alphabets = [(0, 1)] * r if alphabets is None else alphabets
    boolean = all(tuple(values) == (0, 1) for values in alphabets)
    scale = [F(2, max(1, max(values))) for values in alphabets] + [F(1, max(1, bound))] * 2
    scaled_point = [x * s for x, s in zip(point, scale)]
    scaled_basis = [[x * s for x, s in zip(col, scale)] for col in basis]
    reduced, stats["lll_steps"] = reduce_basis(scaled_basis)
    target = [F(1)] * r + [F(0), F(0)]
    target = [x - y for x, y in zip(target, scaled_point)]
    found = set()
    try:
        for vector in sphere_points(reduced, target, r + 2, stats, budget):
            actual = [(x + y) / s for x, y, s in zip(vector, scaled_point, scale)]
            assert all(x.denominator == 1 for x in actual)
            actual = tuple(map(int, actual))
            if boolean and any(x not in (0, 1) for x in actual[:r]):
                raise AssertionError("Boolean sphere separation failed")
            if any(value not in alphabet for value, alphabet in zip(actual[:r], alphabets)):
                continue
            if max(map(abs, actual[-2:])) > bound:
                continue
            if any(sum(actual[j] for j in group) > 1 for group in groups):
                continue
            assert all((dot(row, actual) - value) % mod == 0 for row, value, mod in rows)
            found.add(actual)
    except BudgetExceeded:
        stats["complete"] = False
    return found, stats


def brute_rows(rows, r, bound, groups=()):
    found = set()
    for bits in product((0, 1), repeat=r):
        if any(sum(bits[j] for j in group) > 1 for group in groups):
            continue
        for b, c in product(range(-bound, bound + 1), repeat=2):
            point = bits + (b, c)
            if all((dot(row, point) - value) % mod == 0 for row, value, mod in rows):
                found.add(point)
    return found


def direct_unit(base, deltas, bits, a, precision, b, c):
    target = (base + dot(deltas, bits)) // 2**a
    for modulus in (2 ** (precision - a), 5**precision):
        if pow(3, b, modulus) * pow(7, c, modulus) % modulus != target % modulus:
            return False
    return True


def copy_family_solve(digits, a, block, depth, bound):
    precision = block * depth
    assert precision >= a + 3
    h = max(a + 2, (precision + a + 1) // 2)
    low = [[t for t in range(depth) if e + block * t < h] for _, e in digits]
    result = set()
    statistics = {"low_branches": 0, "lattice_calls": 0, "nodes": 0, "complete": True, "max_rank": 0}
    for choices in product(*(ts + [None] for ts in low)):
        clock_guard()
        statistics["low_branches"] += 1
        occupied = [digits[j][1] + block * t for j, t in enumerate(choices) if t is not None]
        if len(set(occupied)) != len(occupied):
            continue
        base = (10**precision - 1) // 9
        base += sum((digits[j][0] - 1) * 10 ** (digits[j][1] + block * t) for j, t in enumerate(choices) if t is not None)
        if valuation(base, 2) != a or base % 5 == 0:
            continue
        slots = [(j, t, e + block * t) for j, (_, e) in enumerate(digits) if choices[j] is None for t in range(depth) if t not in low[j]]
        deltas = [(digits[j][0] - 1) * 10**position for j, _, position in slots]
        groups = [[i for i, slot in enumerate(slots) if slot[0] == j] for j in range(len(digits))]
        groups += [[i for i, slot in enumerate(slots) if slot[2] == position] for position in {slot[2] for slot in slots}]
        rows = target_rows(base, deltas, a, precision)
        points, stats = box_solve(rows, len(slots), bound, groups)
        statistics["lattice_calls"] += 1
        statistics["nodes"] += stats["nodes"]
        statistics["max_rank"] = max(statistics["max_rank"], len(slots) + 2)
        statistics["complete"] &= stats["complete"]
        for point in points:
            copies = [depth if t is None else t for t in choices]
            for selected, (j, t, _) in zip(point[:-2], slots):
                if selected:
                    copies[j] = t
            result.add(tuple(copies) + point[-2:])
    return result, statistics


def brute_copy_family(digits, a, block, depth, bound):
    precision = block * depth
    result = set()
    for choices in product(range(depth + 1), repeat=len(digits)):
        positions = [e + block * t for (_, e), t in zip(digits, choices) if t < depth]
        if len(set(positions)) != len(positions):
            continue
        target = (10**precision - 1) // 9
        target += sum((d - 1) * 10 ** (e + block * t) for (d, e), t in zip(digits, choices) if t < depth)
        if valuation(target, 2) != a or target % 5 == 0:
            continue
        for b, c in product(range(-bound, bound + 1), repeat=2):
            if direct_unit(target, [], (), a, precision, b, c):
                result.add(choices + (b, c))
    return result


def self_test():
    started = monotonic()
    evidence = {"started": clock_guard(), "runtime": sys.version, "calibration": "COMPUTED, HIGH within finite test scope"}
    rng = Random(154311)
    affine_checks = 0
    for precision in range(5, 11):
        for a in range(min(4, precision - 2)):
            h = max(a + 2, (precision + a + 1) // 2)
            if h >= precision:
                continue
            for trial in range(3):
                deltas = [(1 + trial) * 10**h, 3 * 10 ** min(h + 1, precision - 1)]
                b0, c0 = rng.randrange(8), rng.randrange(8)
                planted = (trial % 2, (trial // 2) % 2)
                modulus = 10**precision
                base = (2**a * pow(3, b0, modulus) * pow(7, c0, modulus) - dot(deltas, planted)) % modulus
                rows = target_rows(base, deltas, a, precision)
                for bits in product((0, 1), repeat=2):
                    for b, c in product(range(-3, 4), repeat=2):
                        point = bits + (b, c)
                        encoded = all((dot(row, point) - target) % mod == 0 for row, target, mod in rows)
                        assert encoded == direct_unit(base, deltas, bits, a, precision, b, c)
                        affine_checks += 1
    evidence["direct_modular_equivalence_checks"] = affine_checks
    total_nodes = total_points = positive = negative = 0
    random_cases = 60
    for i in range(random_cases):
        r, bound = 1 + i % 4, 1 + i % 3
        rows = [([rng.randrange(-5, 6) for _ in range(r + 2)], rng.randrange(mod), mod) for mod in (4, 7, 11)[:1 + i % 3]]
        groups = [(0, 1)] if r > 1 and i % 2 else []
        actual, stats = box_solve(rows, r, bound, groups)
        expected = brute_rows(rows, r, bound, groups)
        assert stats["complete"] and actual == expected, (i, actual, expected, stats)
        positive += bool(expected)
        negative += not expected
        total_nodes += stats["nodes"]
        total_points += stats["sphere_points"]
    evidence["random_lattice_cases"] = {"cases": random_cases, "feasible": positive, "infeasible": negative, "nodes": total_nodes, "sphere_points": total_points}
    combined = []
    for i in range(12):
        precision, a, bound = 6 + i % 3, i % 2, 6
        h = max(a + 2, (precision + a + 1) // 2)
        deltas = [10**h, 2 * 10 ** (h + 1), 3 * 10**h]
        bits = (i % 2, 1 - i % 2, 0)
        b0, c0 = i % 5, (i * 3) % 5
        modulus = 10**precision
        base = (2**a * pow(3, b0, modulus) * pow(7, c0, modulus) - dot(deltas, bits)) % modulus
        parent = ((b0, c0), (2, 0), (1, 3))
        rows = target_rows(base, deltas, a, precision, parent)
        groups = [(0, 1), (0, 2)]
        actual, stats = box_solve(rows, 3, bound, groups)
        expected = set()
        for choice in product((0, 1), repeat=3):
            if any(sum(choice[j] for j in group) > 1 for group in groups):
                continue
            for b, c in product(range(-bound, bound + 1), repeat=2):
                db, dc = b - b0, c - c0
                member = dc % 3 == 0 and (db - dc // 3) % 2 == 0
                if member and direct_unit(base, deltas, choice, a, precision, b, c):
                    expected.add(choice + (b, c))
        assert stats["complete"] and expected == actual
        assert bits + (b0, c0) in actual
        combined.append({"precision": precision, "a": a, "solutions": len(actual), **stats})
    evidence["combined_parent_target_cases"] = combined
    high_precision = []
    u = (-5834300434592217394015440000, -5252227908597256497593760000)
    v = (24550795595028192589139040000, -26061931100684490688131840000)
    for precision, a in ((96, 0), (96, 40), (192, 1)):
        h = max(a + 2, (precision + a + 1) // 2)
        deltas = [10**h, 6 * 10 ** (h + 1)]
        bits, b0, c0, bound = (1, 0), 3, 5, 8
        modulus = 10**precision
        base = (2**a * pow(3, b0, modulus) * pow(7, c0, modulus) - dot(deltas, bits)) % modulus
        rows = target_rows(base, deltas, a, precision, ((b0, c0), u, v))
        actual, stats = box_solve(rows, 2, bound)
        assert stats["complete"] and actual == {bits + (b0, c0)}
        high_precision.append({"precision": precision, "a": a, **stats})
    evidence["high_precision_planted_cases"] = high_precision
    copy_cases = []
    families = [
        ([(6, 1), (5, 0), (6, 1)], 0, 2, 2, 8),
        ([(3, 0), (7, 1)], 0, 2, 2, 6),
        ([(2, 0), (3, 1), (2, 0)], 1, 2, 3, 6),
        ([(4, 0), (2, 1)], 0, 2, 3, 6),
    ]
    for digits, a, block, depth, bound in families:
        actual, stats = copy_family_solve(digits, a, block, depth, bound)
        expected = brute_copy_family(digits, a, block, depth, bound)
        assert stats["complete"] and actual == expected
        copy_cases.append({"digits": digits, "a": a, "block": block, "depth": depth, "bound": bound, "solutions": len(actual), **stats})
    assert (0, 1, 1, 8, 0) in copy_family_solve(*families[0])[0]
    evidence["complete_copy_family_cases"] = copy_cases
    alphabets = [(0, 1, 100), (0, 1)]
    precision, a, b0, c0, bound = 8, 0, 3, 5, 8
    deltas, planted = [10**4, 3 * 10**5], (100, 1)
    modulus = 10**precision
    base = (pow(3, b0, modulus) * pow(7, c0, modulus) - dot(deltas, planted)) % modulus
    rows = target_rows(base, deltas, a, precision)
    actual, stats = box_solve(rows, 2, bound, alphabets=alphabets)
    expected = set()
    for values in product(*alphabets):
        for b, c in product(range(-bound, bound + 1), repeat=2):
            if direct_unit(base, deltas, values, a, precision, b, c):
                expected.add(values + (b, c))
    assert stats["complete"] and actual == expected and planted + (b0, c0) in actual
    negative_rows = [([1, 0, 0], 2, 3), ([0, 1, 0], 0, 100), ([0, 0, 1], 0, 100)]
    negative, negative_stats = box_solve(negative_rows, 1, 1, alphabets=[(0, 1, 100)])
    assert negative_stats["complete"] and not negative and negative_stats["sphere_points"] >= 33
    evidence["sparse_alphabet_cases"] = {"planted_rank4": {"solutions": len(actual), **stats}, "rank3_relaxation_negative": negative_stats}
    log = lambda value: log5_unit(value, 4)
    below = (log(1111 + 10 + 100) - log(1111 + 10) - log(1111 + 100) + log(1111)) % 5**4
    assert below != 0
    precision = 12
    base = (10**precision - 1) // 9
    values = [log5_unit(base + 10 ** (6 + t), precision) for t in range(4)]
    mixed = (values[3] - values[1] - values[2] + values[0]) % 5**precision
    assert mixed != 0
    alpha = 10**4 * pow(1111, -1, 2**8) % 2**8
    exact = principal_log(1 + alpha, 2, 8)
    assert exact != alpha
    _, refused = box_solve([([1, 1, 1], 0, 2)], 1, 1, budget=0)
    assert not refused["complete"]
    evidence["planted_negatives"] = {"below_cutoff_log5_mixed_difference_mod625": below, "copy_index_bits_mixed_difference_mod244140625": mixed, "half_precision_naive_alpha_mod256": alpha, "half_precision_exact_log_mod256": exact, "budget_exhaustion_returns_unknown": not refused["complete"]}
    source_paths = [Path(__file__), Path("tier0/sandwich.py"), Path("tier0/deepcut.py"), Path("tier0/SANDWICH.md"), Path("tier0-opt/math/codex-deep-attempt.md")]
    evidence["sha256"] = {str(path): sha256(path.read_bytes()).hexdigest() for path in source_paths}
    evidence["elapsed_seconds"] = round(monotonic() - started, 3)
    evidence["finished"] = clock_guard()
    evidence["verdict"] = "PASS"
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    clock_guard()
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", required=True)
    parser.parse_args()
    self_test()
