import heapq
import json
import sys
from bisect import bisect_right
from itertools import groupby, pairwise
from math import isqrt

MAX_L = 4_294_967_311
MAX_HORIZON = 125_000
MAX_CORRECTION_STREAMS = 250_000
SLOPES = (-6, -3, 0, 3)


def is_prime(number):
    if number < 2:
        return False
    if number % 2 == 0:
        return number == 2
    return all(number % divisor for divisor in range(3, isqrt(number) + 1, 2))


def binary_chain(exponent):
    value = 1
    for bit in bin(exponent)[3:]:
        value *= 2
        yield value
        if bit == "1":
            value += 1
            yield value


def initial_points(ell, n, with_chain=True):
    result = [(0, 0), (0, 1), (1, 0)]
    present = set(result)
    exponents = (*binary_chain(n), *binary_chain(ell - n - 1)) if with_chain else ()
    for exponent in exponents:
        point = (0, exponent % ell)
        if point not in present:
            present.add(point)
            result.append(point)
    result.append((2, 0))
    return result


def segment_records(ell, n, horizon):
    records = []

    def add(lo, hi, slope, intercept):
        if lo > hi:
            return
        for quotient in range(lo // ell, hi // ell + 1):
            start = max(lo, quotient * ell) - quotient * ell
            stop = min(hi + 1, (quotient + 1) * ell) - quotient * ell
            records.append((start, slope, intercept + slope * quotient * ell, stop))

    for j in range(horizon + 1):
        add(j * n - min(j, horizon), j * n, 0, 3 * j - 2)
        add(j * n - horizon, j * n - j - 1, -3, 3 * j * n - 3)
    for k in range(horizon + 1):
        for parity in (0, 1):
            adjustment = (k * (n + 1) + parity) % 2
            origin = -k * (n + 1) + adjustment * ell
            for first, last, slope, intercept in (
                (0, k, 0, 3 * k - 1),
                (k + 1, horizon, -6, -3 * k * (n + 1) + 3 * adjustment * ell - 3),
            ):
                first += (parity - first) % 2
                last -= (last - parity) % 2
                if first <= last:
                    add((origin - last) // 2, (origin - first) // 2, slope, intercept)
    for d in range(2 * horizon + 1):
        first, last = max(0, d - horizon), min(horizon, d)
        split = (3 * d - 1) // 6
        early_last = min(last, split)
        add(-n * d - early_last, -n * d - first, 3, 3 * d * (n + 1) - 2)
        late_first = max(first, split + 1)
        add(-n * d - last, -n * d - late_first, -3, -3 * n * d - 1)
    records.sort()
    return records


def lower_envelope(ell, records):
    ends = sorted(record[3] for record in records)
    heaps = {slope: [] for slope in SLOPES}
    record_index = end_index = position = 0
    pending = None
    while position < ell:
        while record_index < len(records) and records[record_index][0] == position:
            _, slope, intercept, stop = records[record_index]
            heapq.heappush(heaps[slope], (intercept, stop))
            record_index += 1
        while end_index < len(ends) and ends[end_index] <= position:
            end_index += 1
        stop = ell
        if record_index < len(records):
            stop = min(stop, records[record_index][0])
        if end_index < len(ends):
            stop = min(stop, ends[end_index])
        active = []
        for slope, heap in heaps.items():
            while heap and heap[0][1] <= position:
                heapq.heappop(heap)
            if heap:
                active.append((slope, heap[0][0]))
        if not active:
            raise ArithmeticError(f"uncovered residue {position}")
        boundaries = {position, stop}
        for index, (slope, intercept) in enumerate(active):
            for other_slope, other_intercept in active[index + 1 :]:
                crossing = (other_intercept - intercept) // (slope - other_slope)
                for boundary in (crossing, crossing + 1):
                    if position < boundary < stop:
                        boundaries.add(boundary)
        ordered = sorted(boundaries)
        for start, finish in pairwise(ordered):
            slope, intercept = min(active, key=lambda line: line[0] * start + line[1])
            if pending and pending[1] == start and pending[2:] == (slope, intercept):
                pending = (pending[0], finish, slope, intercept)
            else:
                if pending:
                    yield pending
                pending = (start, finish, slope, intercept)
        position = stop
    if pending:
        yield pending


def progression_bucket(ell, origin, step, first, last, time_origin, time_step):
    indices = range(first, last + 1) if step > 0 else range(last, first - 1, -1)
    for index in indices:
        yield (origin + step * index) % ell, time_origin + time_step * index


def progression_streams(ell, origin, step, count, time_origin, time_step):
    endpoint = origin + step * (count - 1)
    low, high = sorted((origin, endpoint))
    for quotient in range(low // ell, high // ell + 1):
        lower, upper = quotient * ell, (quotient + 1) * ell - 1
        if step > 0:
            first = max(0, -((origin - lower) // step))
            last = min(count - 1, (upper - origin) // step)
        else:
            magnitude = -step
            first = max(0, -((upper - origin) // magnitude))
            last = min(count - 1, (origin - lower) // magnitude)
        if first <= last:
            yield progression_bucket(ell, origin, step, first, last, time_origin, time_step)


def progression_bucket_count(ell, origin, step, count):
    if count <= 0:
        return 0
    if not 0 < abs(step) < ell:
        raise ValueError("progression step magnitude must be in [1, l - 1]")
    endpoint = origin + step * (count - 1)
    return abs(endpoint // ell - origin // ell) + 1


def correction_stream_count(ell, n, horizon, initial):
    total = 0
    for kind, baby in initial:
        if kind != 0:
            continue
        total += 2 + progression_bucket_count(ell, n - baby, n, horizon)
        for first_k in (2, 1):
            if first_k > horizon:
                continue
            adjustment = (first_k * (n + 1) + baby) % 2
            origin = (-first_k * (n + 1) - baby + adjustment * ell) // 2
            count = (horizon - first_k) // 2 + 1
            total += progression_bucket_count(ell, origin, -(n + 1), count)
    return total


def initial_corrections(ell, n, horizon, initial):
    length = len(initial)
    streams = []
    for index, (kind, baby) in enumerate(initial):
        if kind != 0:
            continue
        baby_time = index - length
        streams.append(iter((((-baby) % ell, max(baby_time, 2 - length)),)))
        streams.extend(progression_streams(ell, n - baby, n, horizon, 1, 3))
        streams.append(iter((((-baby * pow(2, -1, ell)) % ell, max(baby_time, -1)),)))
        for parity in (0, 1):
            first_k = 2 if parity == 0 else 1
            if first_k > horizon:
                continue
            adjustment = (first_k * (n + 1) + baby) % 2
            origin = (-first_k * (n + 1) - baby + adjustment * ell) // 2
            count = (horizon - first_k) // 2 + 1
            streams.extend(progression_streams(ell, origin, -(n + 1), count, 3 * first_k - 1, 6))
    for residue, group in groupby(heapq.merge(*streams), key=lambda item: item[0]):
        yield residue, min(item[1] for item in group)


def count_above(start, stop, slope, intercept, threshold):
    if slope == 0:
        return stop - start if intercept >= threshold else 0
    if slope > 0:
        first = -((intercept - threshold) // slope)
        return max(0, stop - max(start, first))
    last = (intercept - threshold) // (-slope)
    return max(0, min(stop, last + 1) - start)


def aggregate(start, stop, slope, intercept, length, thresholds):
    count = stop - start
    if not count:
        return 0, -1
    total = length * count + slope * (start + stop - 1) * count // 2 + intercept * count
    total -= sum(count_above(start, stop, slope, intercept, threshold) for threshold in thresholds)
    endpoint = stop - 1 if slope >= 0 else start
    raw_last = slope * endpoint + intercept
    last = length + raw_last - bisect_right(thresholds, raw_last)
    return total, last


def maximum(start, stop, slope, intercept, length, thresholds):
    if start >= stop:
        return -1
    endpoint = stop - 1 if slope >= 0 else start
    raw_time = slope * endpoint + intercept
    return length + raw_time - bisect_right(thresholds, raw_time)


def evaluate(ell, n, with_chain):
    if type(ell) is not int or not 3 <= ell <= MAX_L:
        raise ValueError(f"l must be an integer in [3, {MAX_L}]")
    if not is_prime(ell):
        raise ValueError("l must be prime")
    if type(n) is not int or not 1 <= n <= ell - 2:
        raise ValueError("n must be an integer in [1, l - 2]")
    horizon = max(n - 1, (ell + n - 2) // n)
    if horizon > MAX_HORIZON:
        raise ValueError(f"exact evaluator horizon {horizon} exceeds resource limit {MAX_HORIZON}")
    initial = initial_points(ell, n, with_chain)
    stream_count = correction_stream_count(ell, n, horizon, initial)
    if stream_count > MAX_CORRECTION_STREAMS:
        raise ValueError(
            f"exact evaluator correction streams {stream_count} exceed resource limit {MAX_CORRECTION_STREAMS}"
        )
    length = len(initial)
    thresholds = tuple(sorted(3 * (baby - 1) for kind, baby in initial if kind == 0 and 1 <= baby <= horizon))
    records = segment_records(ell, n, horizon)
    corrections = iter(initial_corrections(ell, n, horizon, initial))
    correction = next(corrections, None)
    total = last = 0
    for start, stop, slope, intercept in lower_envelope(ell, records):
        subtotal, _ = aggregate(start, stop, slope, intercept, length, thresholds)
        total += subtotal
        position = start
        while correction is not None and correction[0] < stop:
            residue, raw_time = correction
            last = max(last, maximum(position, residue, slope, intercept, length, thresholds))
            baseline_raw = slope * residue + intercept
            raw_time = min(raw_time, baseline_raw)
            actual = length + raw_time - bisect_right(thresholds, raw_time)
            baseline = length + baseline_raw - bisect_right(thresholds, baseline_raw)
            total += actual - baseline
            last = max(last, actual)
            position = residue + 1
            correction = next(corrections, None)
        last = max(last, maximum(position, stop, slope, intercept, length, thresholds))
    return total, last


def weight(ell, n):
    return evaluate(ell, n, True)


def weight_chain_free(ell, n):
    return evaluate(ell, n, False)


def main():
    request = json.load(sys.stdin)
    total, last = weight(request["l"], request["n"])
    print(json.dumps({"W": total, "last": last}, separators=(",", ":")))


if __name__ == "__main__":
    main()
