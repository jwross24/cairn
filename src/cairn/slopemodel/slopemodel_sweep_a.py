import json
import sys
from bisect import bisect_right
from math import isqrt

MAX_L = 2**62
WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
PACK_BITS = 64


def is_prime(number: int) -> bool:
    if number < 2:
        return False
    for prime in WITNESSES:
        if number % prime == 0:
            return number == prime
    odd, powers = number - 1, 0
    while odd % 2 == 0:
        odd //= 2
        powers += 1
    for base in WITNESSES:
        residue = pow(base, odd, number)
        if residue in (1, number - 1):
            continue
        for _ in range(powers - 1):
            residue = residue * residue % number
            if residue == number - 1:
                break
        else:
            return False
    return True


def binary_chain(exponent: int) -> list[int]:
    accumulator = 1
    result = []
    for bit in bin(exponent)[3:]:
        accumulator *= 2
        result.append(accumulator)
        if bit == "1":
            accumulator += 1
            result.append(accumulator)
    return result


def initial_points(ell: int, n: int, with_chains: bool = True) -> list[tuple[int, int]]:
    raw = [(0, 0), (0, 1), (1, 0)]
    if with_chains:
        raw.extend((0, exponent) for exponent in binary_chain(n))
        raw.extend((0, exponent) for exponent in binary_chain(ell - n - 1))
    raw.append((2, 0))
    seen = set()
    result = []
    for x, y in raw:
        point = (x, y % ell)
        if point not in seen:
            seen.add(point)
            result.append(point)
    return result


def initial_pair_pieces(ell: int, initial: list[tuple[int, int]]) -> list[tuple[int, int, int, int]]:
    inverse = {difference: pow(difference % ell, -1, ell) for difference in (-2, -1, 1, 2)}
    count = len(initial)
    first_index: dict[int, int] = {}
    for index, (x, y) in enumerate(initial):
        for previous_x, previous_y in initial[:index]:
            if previous_x == x:
                continue
            slope = (previous_y - y) * inverse[previous_x - x] % ell
            if slope not in first_index:
                first_index[slope] = index
    return [(slope, slope, index - count + 3, 0) for slope, index in first_index.items()]


def family_pieces(ell: int, n: int, horizon: int, out: list[tuple[int, int, int, int]]) -> None:
    half = (ell + 1) // 2
    shift = (ell - 1) // 2

    def add(lo: int, hi: int, a: int, b: int) -> None:
        if lo > hi:
            return
        wraps = lo // ell
        lo -= wraps * ell
        hi -= wraps * ell
        a += b * wraps * ell
        if hi < ell:
            out.append((lo, hi, a, b))
        else:
            out.append((lo, ell - 1, a, b))
            out.append((0, hi - ell, a + b * ell, b))

    for t in range(horizon + 1):
        top = t * n
        add(top - t, top, 3 * t + 1, 0)
        add(top - horizon, top - t - 1, 3 * top, -3)
    even_max = horizon // 2
    odd_max = (horizon - 1) // 2
    for u in range(horizon + 1):
        center = -u * (n + 1) * half % ell
        kappa = 3 * u + 2
        even_split = (3 * u + 2) // 6
        add(center - min(even_max, even_split), center, kappa, 0)
        add(center - even_max, center - even_split - 1, 6 * center, -6)
        odd_center = center + shift
        odd_split = (3 * u - 1) // 6
        add(odd_center - min(odd_max, odd_split), odd_center, kappa, 0)
        add(odd_center - odd_max, odd_center - max(0, odd_split + 1), 6 * odd_center + 3, -6)
    for v in range(2 * horizon + 1):
        low = max(0, v - horizon)
        high = min(v, horizon)
        split = (3 * v - 1) // 6
        base = -v * n
        add(base - min(split, high), base - low, 3 * v + 1 + 3 * v * n, 3)
        add(base - high, base - max(split + 1, low), 2 - 3 * v * n, -3)


def lower_envelope(first: int, last: int, lines: list[tuple[int, int]]) -> list[tuple[int, int, int]]:
    position = first
    segments = []
    while position <= last:
        best_value = None
        best_slope = best_a = 0
        for a, b in lines:
            value = a + b * position
            if best_value is None or value < best_value or (value == best_value and b < best_slope):
                best_value = value
                best_slope = b
                best_a = a
        stop = last + 1
        for a, b in lines:
            if b < best_slope:
                crossing = (a - best_a) // (best_slope - b) + 1
                if crossing <= position:
                    crossing = position + 1
                if crossing < stop:
                    stop = crossing
        segments.append((position, best_a, best_slope))
        position = stop
    return segments


def build_table(ell: int, pieces: list[tuple[int, int, int, int]]):
    pieces.sort()
    boundaries = sorted({0, ell} | {piece[0] for piece in pieces} | {piece[1] + 1 for piece in pieces})
    starts: list[int] = []
    table_a: list[int] = []
    table_b: list[int] = []
    active: list[tuple[int, int, int, int]] = []
    cursor = 0
    piece_count = len(pieces)
    for position in range(len(boundaries) - 1):
        left = boundaries[position]
        right = boundaries[position + 1]
        if active:
            active = [piece for piece in active if piece[1] >= left]
        while cursor < piece_count and pieces[cursor][0] == left:
            active.append(pieces[cursor])
            cursor += 1
        if not active:
            return None
        if len(active) == 1:
            segments = [(left, active[0][2], active[0][3])]
        else:
            segments = lower_envelope(left, right - 1, [(piece[2], piece[3]) for piece in active])
        for start, a, b in segments:
            if table_a and table_a[-1] == a and table_b[-1] == b:
                continue
            starts.append(start)
            table_a.append(a)
            table_b.append(b)
    return starts, table_a, table_b


def skipped_prefix_sums(skipped: set[int], horizon: int):
    size = horizon + 4
    skipped_by = [0] * size
    for t in range(1, size):
        skipped_by[t] = skipped_by[t - 1] + (1 if t in skipped else 0)
    step_one = [0] * size
    step_two = [0] * size
    for t in range(size):
        step_one[t] = (step_one[t - 1] if t else 0) + skipped_by[t]
        step_two[t] = skipped_by[t] + (step_two[t - 2] if t >= 2 else 0)
    return skipped_by, step_one, step_two


def sweep(ell: int, n: int, horizon: int, initial: list[tuple[int, int]]):
    extras = sorted({y for x, y in initial if x == 0})
    pieces = initial_pair_pieces(ell, initial)
    family_pieces(ell, n, horizon, pieces)
    table = build_table(ell, pieces)
    if table is None:
        return None
    starts, table_a, table_b = table
    del pieces
    skipped_by, step_one, step_two = skipped_prefix_sums(set(extras), horizon)

    def skipped_before(kappa: int) -> int:
        t = kappa // 3
        return skipped_by[t] if t > 0 else 0

    def run_sum_one(lo: int, hi: int) -> int:
        if hi <= 0:
            return 0
        return step_one[hi] - (step_one[lo - 1] if lo >= 1 else 0)

    def run_sum_two(lo: int, hi: int) -> int:
        if hi <= 0:
            return 0
        return step_two[hi] - (step_two[lo - 2] if lo >= 2 else 0)

    segment_count = len(starts)
    sum_kappa = 0
    sum_skipped = 0
    for i in range(segment_count):
        lo = starts[i]
        hi = (starts[i + 1] if i + 1 < segment_count else ell) - 1
        a = table_a[i]
        b = table_b[i]
        length = hi - lo + 1
        sum_kappa += length * a + b * (lo + hi) * length // 2
        if b == 0:
            sum_skipped += length * skipped_before(a)
            continue
        round_first = (a + b * lo) // 3
        round_last = (a + b * hi) // 3
        if abs(b) == 3:
            sum_skipped += run_sum_one(min(round_first, round_last), max(round_first, round_last))
        elif abs(b) == 6:
            sum_skipped += run_sum_two(min(round_first, round_last), max(round_first, round_last))
        else:
            raise AssertionError(b)

    half = (ell + 1) // 2
    giant_two_step = -(n + 1) * half % ell
    mask = (1 << PACK_BITS) - 1
    lowered: dict[int, int] = {}
    for extra in extras:
        x_one = -extra % ell
        x_two = -extra * half % ell
        for t in range(1, horizon + 1):
            x_one += n
            if x_one >= ell:
                x_one -= ell
            x_two += giant_two_step
            if x_two >= ell:
                x_two -= ell
            for x, kappa in ((x_one, 3 * t + 1), (x_two, 3 * t + 2)):
                i = bisect_right(starts, x) - 1
                base = table_a[i] + table_b[i] * x
                if kappa < base:
                    previous = lowered.get(x)
                    if previous is None or kappa < previous >> PACK_BITS:
                        lowered[x] = kappa << PACK_BITS | base

    max_kappa = None
    for packed in lowered.values():
        kappa = packed >> PACK_BITS
        base = packed & mask
        sum_kappa += kappa - base
        sum_skipped += skipped_before(kappa) - skipped_before(base)
        if max_kappa is None or kappa > max_kappa:
            max_kappa = kappa
    for i in range(segment_count):
        lo = starts[i]
        hi = (starts[i + 1] if i + 1 < segment_count else ell) - 1
        b = table_b[i]
        if b > 0:
            x = hi
            while x >= lo and x in lowered:
                x -= 1
            if x < lo:
                continue
        else:
            x = lo
            while x <= hi and x in lowered:
                x += 1
            if x > hi:
                continue
        value = table_a[i] + b * x
        if max_kappa is None or value > max_kappa:
            max_kappa = value

    count = len(initial)
    total = (count - 3) * ell + sum_kappa - sum_skipped
    assert max_kappa is not None
    last = count - 3 + max_kappa - skipped_before(max_kappa)
    return total, last


def checked_weight(ell: int, n: int, with_chains: bool) -> tuple[int, int]:
    if type(ell) is not int or not 3 <= ell <= MAX_L:
        raise ValueError(f"l must be an integer in [3, {MAX_L}]")
    if not is_prime(ell):
        raise ValueError("l must be prime")
    if type(n) is not int or not 1 <= n <= ell - 2:
        raise ValueError("n must be an integer in [1, l - 2]")
    initial = initial_points(ell, n, with_chains)
    horizon = min(ell - 1, isqrt(ell) * 5 // 4 + 16)
    while True:
        result = sweep(ell, n, horizon, initial)
        if result is not None:
            return result
        if horizon >= ell - 1:
            raise ValueError("schedule did not determine every slope")
        horizon = min(2 * horizon, ell - 1)


def weight(ell: int, n: int) -> tuple[int, int]:
    return checked_weight(ell, n, True)


def weight_chain_free(ell: int, n: int) -> tuple[int, int]:
    return checked_weight(ell, n, False)


def main() -> None:
    request = json.load(sys.stdin)
    total, last = weight(request["l"], request["n"])
    print(json.dumps({"W": total, "last": last}))


if __name__ == "__main__":
    main()
