from math import sqrt

A_LOW = 0.5
A_HIGH = 1 / sqrt(3)
TOLERANCE = 1e-6
POSITION_OFFSET = 0.3819660112501051

GAUSS_NODES = (-sqrt(3 / 5), 0.0, sqrt(3 / 5))
GAUSS_WEIGHTS = (5 / 9, 8 / 9, 5 / 9)


def check_range(a: float) -> None:
    if not A_LOW - TOLERANCE <= a <= A_HIGH + TOLERANCE:
        raise ValueError("derived for 1/2 <= alpha <= 1/sqrt(3)")


def g_without_strip(a: float) -> float:
    return (
        3 * a
        - 45 * a**3 / 16
        + (1 - 2 * a * a) ** 3 / (32 * a**3)
        + (1 - 3 * a * a) ** 2 / (4 * a)
    )


def g_strip_mean(a: float) -> float:
    return (4 * a * a - 1) ** 3 * (12 * a * a + 1) / (512 * a**5)


def g_mean(a: float) -> float:
    check_range(a)
    return g_without_strip(a) + g_strip_mean(a)


def strip_overlap(tau: float, a: float, offset: float) -> float:
    s0 = 1 / (2 * a)
    left = -tau
    right = tau - s0
    if right <= left:
        return 0.0
    period = a / 2
    width = tau / 2
    k_low = int((left - offset) // period) - 1
    k_high = int((right - offset) // period) + 1
    total = 0.0
    for k in range(k_low, k_high + 1):
        lo = max(left, offset + k * period)
        hi = min(right, offset + k * period + width)
        if hi > lo:
            total += ((right - lo) ** 2 - (right - hi) ** 2) / 2
    return total


def strip_breakpoints(a: float, offset: float) -> list[float]:
    s0 = 1 / (2 * a)
    period = a / 2
    first = s0 / 2
    points = {first, a}
    for k in range(-12, 13):
        base = offset + k * period
        for tau in (-base, -base / 1.5, s0 + base, 2 * (s0 + base)):
            if first < tau < a:
                points.add(tau)
    return sorted(points)


def strip_integral(a: float, offset: float) -> float:
    points = strip_breakpoints(a, offset)
    total = 0.0
    for left, right in zip(points, points[1:]):
        half = (right - left) / 2
        middle = (right + left) / 2
        for node, weight in zip(GAUSS_NODES, GAUSS_WEIGHTS):
            total += weight * half * strip_overlap(middle + half * node, a, offset)
    return total


def phase_offset(ell: int, n: int) -> float:
    root = sqrt(ell)
    a = n / root
    rho = (((ell + 1) // 2) % n) / root
    return rho - 1 / (2 * a)


def g_phase_unchecked(a: float, offset: float) -> float:
    return g_without_strip(a) + 3 * strip_integral(a, offset)


def g_phase(a: float, offset: float) -> float:
    check_range(a)
    return g_phase_unchecked(a, offset)


def g_phase_for(ell: int, n: int) -> float:
    return g_phase(n / sqrt(ell), phase_offset(ell, n))


def g(alpha: float) -> float:
    return g_mean(alpha)


def union_length(intervals: list[tuple[float, float]], period: float) -> float:
    pieces = []
    for lo, hi in intervals:
        if hi - lo >= period:
            return period
        start = lo % period
        stop = start + (hi - lo)
        if stop > period:
            pieces.append((start, period))
            pieces.append((0.0, stop - period))
        else:
            pieces.append((start, stop))
    pieces.sort()
    total = 0.0
    current_lo = current_hi = None
    for lo, hi in pieces:
        if current_hi is None or lo > current_hi:
            if current_hi is not None:
                total += current_hi - current_lo
            current_lo, current_hi = lo, hi
        elif hi > current_hi:
            current_hi = hi
    if current_hi is not None:
        total += current_hi - current_lo
    return total


def covered_fraction(p: float, tau: float, a: float, lam: float, rho: float) -> float:
    intervals = []
    if p <= tau * a:
        intervals.append((-tau, 0.0))
    y = 1 - p
    if 0 < y <= 2 * tau * a:
        s = y / a
        intervals.append((lam - min(s, tau), lam - max(0.0, s - tau)))
    if 0 < y <= tau * a / 2:
        s = y / a
        for k in (0, 1):
            intervals.append((lam - s - k * a / 2 - tau / 2, lam - s - k * a / 2))
    if 0.5 <= y <= 0.5 + tau * a / 2:
        sigma = (y - 0.5) / a
        for k in (0, 1):
            intervals.append((lam - sigma - rho - k * a / 2 - tau / 2, lam - sigma - rho - k * a / 2))
    if not intervals:
        return 0.0
    return union_length(intervals, a) / a


def uncovered_fraction(tau: float, a: float, lam: float, rho: float, position_steps: int) -> float:
    step = 1.0 / position_steps
    covered = sum(covered_fraction((i + POSITION_OFFSET) * step, tau, a, lam, rho) for i in range(position_steps))
    return 1 - covered * step


def g_local(a: float, rho: float, time_steps: int = 1000, position_steps: int = 6000) -> float:
    lam = (2 * rho) % a
    end = min(2 * a, 2 / (3 * a))
    step = end / time_steps
    total = sum(uncovered_fraction((i + 0.5) * step, a, lam, rho, position_steps) for i in range(time_steps))
    return 3 * total * step


def g_local_for(ell: int, n: int, **options) -> float:
    root = sqrt(ell)
    return g_local(n / root, (((ell + 1) // 2) % n) / root, **options)
