from math import isqrt

MAX_L = 4_194_304
MR_BASES = (2, 3, 5, 7, 11)


def is_prime(number: int) -> bool:
    if number < 2:
        return False
    for prime in MR_BASES:
        if number % prime == 0:
            return number == prime
    odd, powers = number - 1, 0
    while odd % 2 == 0:
        odd //= 2
        powers += 1
    for base in MR_BASES:
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


def next_prime(t: int) -> int:
    if type(t) is not int or not 3 <= t <= MAX_L:
        raise ValueError(f"t must be an integer in [3, {MAX_L}]")
    number = t
    while number <= MAX_L:
        if is_prime(number):
            return number
        number += 1
    raise ValueError("next prime exceeds l bound")


def chain_exponents(exponent: int) -> list[int]:
    if exponent == 1:
        return []
    parent = exponent >> 1
    operations = [*chain_exponents(parent), 2 * parent]
    if exponent & 1:
        operations.append(exponent)
    return operations


def build_points(ell: int, n: int, horizon: int) -> list[tuple[int, int]]:
    result = [(0, 0), (0, 1), (1, 0)]
    present = set(result)

    def push(x: int, y: int) -> None:
        point = (x % ell, y % ell)
        if point not in present and len(result) < horizon:
            present.add(point)
            result.append(point)

    for exponent in chain_exponents(n):
        push(0, exponent)
    for exponent in chain_exponents(ell - n - 1):
        push(0, exponent)
    push(2, 0)
    baby_y = giant_one_y = giant_two_y = 0
    while len(result) < horizon:
        baby_y += 1
        push(0, baby_y)
        giant_one_y += n
        push(1, giant_one_y)
        giant_two_y += ell - n - 1
        push(2, giant_two_y)
    return result


def first_times_pairs(ell: int, points: list[tuple[int, int]]) -> dict[int, int]:
    first: dict[int, int] = {}
    inverse: dict[int, int] = {}
    for lo, (xlo, ylo) in enumerate(points):
        for hi in range(lo + 1, len(points)):
            xhi, yhi = points[hi]
            difference = (xhi - xlo) % ell
            if difference == 0:
                continue
            multiplier = inverse.get(difference)
            if multiplier is None:
                multiplier = inverse[difference] = pow(difference, -1, ell)
            slope = (yhi - ylo) * multiplier % ell
            previous = first.get(slope)
            if previous is None or hi < previous:
                first[slope] = hi
    return first


def weight(ell: int, n: int) -> tuple[int, int]:
    if type(ell) is not int or not 3 <= ell <= MAX_L:
        raise ValueError(f"l must be an integer in [3, {MAX_L}]")
    if not is_prime(ell):
        raise ValueError("l must be prime")
    if type(n) is not int or not 1 <= n <= ell - 2:
        raise ValueError("n must be an integer in [1, l - 2]")
    horizon = min(4 * isqrt(ell) + 64, 3 * ell)
    while True:
        first = first_times_pairs(ell, build_points(ell, n, horizon))
        if len(first) == ell:
            return sum(first.values()), max(first.values())
        if horizon == 3 * ell:
            raise ValueError("schedule did not determine every slope")
        horizon = min(horizon * 2, 3 * ell)
