BASE = 10
NODE_LIMIT = int(5e8)


class Budget(Exception):
    pass


class Reached(Exception):
    pass


POW10 = [BASE ** i for i in range(4096)]


def v2(x):
    return (x & -x).bit_length() - 1


def exact_max_v2(M, slack=0, leading_lo=1, node_limit=NODE_LIMIT, stats=None, target=None):
    counts = {}
    for d in M:
        counts[d] = counts.get(d, 0) + 1
    kinds = sorted(counts)
    steps = {d: (BASE - 1) * (d - 1) for d in kinds}
    nodes = [0]
    left = [sum(counts.values())]

    def value(a, T):
        nodes[0] += 1
        if nodes[0] > node_limit:
            raise Budget(nodes[0])
        v = v2(T)
        if target is not None and v >= target:
            raise Reached(v)
        top = v + slack
        best = v
        if left[0] == 0:
            for L in range(a + leading_lo, top + 1):
                w = v2(T + POW10[L])
                if target is not None and w >= target:
                    raise Reached(w)
                if w > best:
                    best = w
            return best
        for d in kinds:
            if counts[d] == 0:
                continue
            counts[d] -= 1
            left[0] -= 1
            step = steps[d]
            for t in range(a + 1, top + 1):
                w = value(t, T + step * POW10[t])
                if w > best:
                    best = w
            counts[d] += 1
            left[0] += 1
        return best

    best = 0
    for d in kinds:
        if d % 2:
            continue
        counts[d] -= 1
        left[0] -= 1
        w = value(0, steps[d] - 1)
        counts[d] += 1
        left[0] += 1
        if w > best:
            best = w
    if stats is not None:
        stats["nodes"] = nodes[0]
    return best


def two_adic_bound(M, kcap=200):
    r = exact_max_v2(tuple(M))
    if r >= kcap:
        raise RuntimeError("2-adic bound did not terminate")
    return r
