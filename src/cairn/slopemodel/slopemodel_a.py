from collections.abc import Iterator
from math import isqrt

READING = "bl2012-two-grumpy-giants/fitted-1"
MAX_L = 2**22


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


def points(ell: int, n: int) -> Iterator[tuple[int, int]]:
    seen = set()
    initial = [(0, 0), (0, 1), (1, 0)]
    initial.extend((0, exponent) for exponent in binary_chain(n))
    initial.extend((0, exponent) for exponent in binary_chain(ell - n - 1))
    initial.append((2, 0))
    for x, y in initial:
        point = (x, y % ell)
        if point not in seen:
            seen.add(point)
            yield point
    for t in range(1, ell + 1):
        for x, y in ((0, t), (1, t * n), (2, -t * (n + 1))):
            point = (x, y % ell)
            if point not in seen:
                seen.add(point)
                yield point


def weight(ell: int, n: int) -> tuple[int, int]:
    if type(ell) is not int or not 3 <= ell <= MAX_L:
        raise ValueError(f"l must be an integer in [3, {MAX_L}]")
    if any(ell % divisor == 0 for divisor in range(2, isqrt(ell) + 1)):
        raise ValueError("l must be prime")
    if type(n) is not int or not 1 <= n <= ell - 2:
        raise ValueError("n must be an integer in [1, l - 2]")
    inverse = {difference: pow(difference % ell, -1, ell) for difference in (-2, -1, 1, 2)}
    earlier: list[list[int]] = [[], [], []]
    discovered = bytearray(ell)
    found = total = last = 0
    for index, (x, y) in enumerate(points(ell, n)):
        for previous_x, previous_ys in enumerate(earlier):
            if previous_x == x:
                continue
            multiplier = inverse[previous_x - x]
            for previous_y in previous_ys:
                slope = (previous_y - y) * multiplier % ell
                if not discovered[slope]:
                    discovered[slope] = 1
                    total += index
                    found += 1
                    last = index
        earlier[x].append(y)
        if found == ell:
            return total, last
    raise ValueError("schedule did not determine every slope")
