import sys, json, time, itertools
sys.dont_write_bytecode = True
from joint import *
from count import multisets, DIG

import os
NEG = os.environ.get('NEG') == '1'
NEGD = int(os.environ.get('NEGD', '4'))
SRC = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"


def vertex_record(s):
    for f in ("runall_final.jsonl", "trees_mac.jsonl", "trees_c.jsonl"):
        for l in open(SRC + f):
            r = json.loads(l)
            if r["s"] == s:
                return r
    raise KeyError(s)


def exps(s):
    e = []
    for p in (2, 3, 7):
        k = 0
        while s % p == 0:
            s //= p
            k += 1
        e.append(k)
    assert s == 1
    return e


def words(length, alpha_counts, digits):
    out = []

    def rec(i, cur, rem, used):
        if i == length:
            out.append((int("".join(map(str, cur))), tuple(sorted(used.items()))))
            return
        cur.append(1)
        rec(i + 1, cur, rem, used)
        cur.pop()
        for d in digits:
            if rem.get(d, 0) > 0:
                rem[d] -= 1
                used[d] = used.get(d, 0) + 1
                cur.append(d)
                rec(i + 1, cur, rem, used)
                cur.pop()
                used[d] -= 1
                if used[d] == 0:
                    del used[d]
                rem[d] += 1

    rec(0, [], dict(alpha_counts), {})
    return out


def is_child(y, M):
    t = str(y)
    if "0" in t or "5" in t:
        return False
    nz = sorted(int(ch) for ch in t if ch != "1")
    return nz == sorted(d for d, c in M.items() for _ in range(c))


def small_scan(M, nlim):
    found = set()
    top = 10**nlim
    a = 0
    while 2**a < top:
        b = 0
        while 2**a * 3**b < top:
            c = 0
            while 2**a * 3**b * 7**c < top:
                y = 2**a * 3**b * 7**c
                if is_child(y, M):
                    found.add(y)
                c += 1
            b += 1
        a += 1
    return found


def run_equation(M, P, K, nmax, stats, log2_10=3.3219280948873623):
    digits = sorted(d for d, c in M.items() if c)
    heads = words(P, M, digits)
    tails = words(K, M, digits)
    found = set()
    amax = int(nmax * log2_10) + 2
    for D, uh in heads:
        uhd = dict(uh)
        for Bt, ut in tails:
            if any(uhd.get(d, 0) + c > M.get(d, 0) for d, c in ut):
                continue
            if Bt % 5 == 0 or Bt % 2 == 0 and False:
                continue
            if NEG and Bt % 10 == NEGD:
                continue
            stats["pairs"] += 1
            if Bt % (1 << K) == 0:
                stats["a_free_pairs"] += 1
                for a in range(K, amax + 1):
                    for r in query_fixed_a(D, P, Bt, K, a, P + K, nmax, stats):
                        stats["queries"] += 1
                        if verify_candidate(*r, D, P, Bt, K):
                            found.add(2 ** r[0] * 3 ** r[1] * 7 ** r[2])
                continue
            stats["queries"] += 1
            for r in query(D, P, Bt, K, P + K, nmax, stats):
                y = 2 ** r[0] * 3 ** r[1] * 7 ** r[2]
                if is_child(y, M):
                    found.add(y)
    byq = {y for y in found if is_child(y, M)}
    scan = small_scan(M, P + K - 1)
    return byq, scan


if __name__ == "__main__":
    s = int(sys.argv[1])
    P = int(sys.argv[2])
    K = int(sys.argv[3])
    nmax = int(sys.argv[4])
    rec = vertex_record(s)
    known = {y for y in rec["known"] if len(str(y)) <= nmax}
    t0 = time.time()
    allf = set()
    allq = set()
    tot = {"pairs": 0, "a_free_pairs": 0, "queries": 0, "enum_points": 0, "coset_empty": 0}
    for M in multisets(exps(s)):
        k = sum(M.values())
        st = {"pairs": 0, "a_free_pairs": 0, "queries": 0, "enum_points": 0, "coset_empty": 0}
        fq, fs = run_equation(M, P, K, nmax, st)
        allf |= fq | fs
        allq |= fq
        for kk in tot:
            tot[kk] += st.get(kk, 0)
    print(json.dumps({"s": s, "P": P, "K": K, "nmax": nmax, "multisets": len(multisets(exps(s))), **tot,
                      "found": sorted(allf), "found_by_pair_query": sorted(allq), "recorded_known": sorted(known), "agree": allf == known,
                      "secs": round(time.time() - t0, 1)}))
