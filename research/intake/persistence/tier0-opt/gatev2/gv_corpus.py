import os, sys, re, json, random, itertools
from math import comb
from collections import Counter

_ready = {}


def init_py(work):
    src = os.path.join(work, 'src')
    if src not in sys.path:
        sys.path.insert(0, src)
    if 'done' in _ready:
        return
    import export_level as el
    orig = el.level_chain
    cache = {}

    def lc(M, upto):
        if upto not in cache:
            cache[upto] = orig(M, upto)
        return cache[upto]
    el.level_chain = lc
    _ready['done'] = True


def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p


def mkey(M):
    return ''.join(map(str, M))


def export12(work, M):
    init_py(work)
    from export_cfg import export
    p = os.path.join(work, 'cfg', f'c12_{mkey(M)}.txt')
    jp = p + '.info'
    if not os.path.exists(jp):
        cfg = export(M, p)
        json.dump(dict(A=cfg['A'], K=cfg['K'], np=len(cfg['primes']), nc=len(cfg['comps']), U2=cfg['U2'], N=cfg['N'], g=cfg['g']), open(jp + '.tmp', 'w'))
        os.replace(jp + '.tmp', jp)
        if os.path.exists(p + '.json'):
            os.remove(p + '.json')
    return p, json.load(open(jp))


def exportN(work, M, L):
    init_py(work)
    from export_level import export
    p = os.path.join(work, 'cfg', f'c{L}_{mkey(M)}.txt')
    jp = p + '.info'
    if not os.path.exists(jp):
        info = export(M, L, p)
        json.dump(info, open(jp + '.tmp', 'w'))
        os.replace(jp + '.tmp', jp)
    return p, json.load(open(jp))


def tierA_vertices():
    out = []
    for ln in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tier0', 'FRONTIER.md')):
        m = re.match(r'\|\s*A\s*\|\s*A_\d\s*\|\s*(\d+)\s*\|', ln)
        if m:
            out.append(int(m.group(1)))
    return out


def multisets(s):
    out = []

    def rec(n, mind, cur):
        if n == 1:
            out.append(tuple(cur))
            return
        for d in range(mind, 10):
            if n % d == 0:
                cur.append(d)
                rec(n // d, d, cur)
                cur.pop()
    rec(s, 2, [])
    return out


def build_corpus(seed=20261020, n=520, cap=4_000_000, nA=240, capA=30_000_000):
    rng = random.Random(seed)
    eqs, seen = [], set()

    def add(M, tag):
        M = tuple(sorted(M))
        if M in seen or len(M) < 1:
            return False
        seen.add(M)
        s = 1
        for d in M:
            s *= d
        eqs.append(dict(id=f'e{len(eqs):03d}', s=s, M=list(M), tag=tag, npat=npat(M)))
        return True

    byv = {}
    for s in tierA_vertices():
        ms = [M for M in multisets(s) if npat(M) <= capA and len(M) >= 2]
        rng.shuffle(ms)
        byv[s] = ms
    rounds = 0
    while sum(1 for e in eqs if e['tag'] == 'tierA') < nA and rounds < 20:
        for s in sorted(byv):
            if byv[s] and sum(1 for e in eqs if e['tag'] == 'tierA') < nA:
                add(byv[s].pop(), 'tierA')
        rounds += 1
    profiles = {
        'tiny': (2, 4, range(2, 10)),
        'mid': (5, 7, range(2, 10)),
        'pow2': (6, 14, (2, 4, 8)),
        'pow2+3': (5, 12, (2, 3, 4, 6, 8, 9)),
        'sev': (5, 14, (7, 2, 4, 6)),
        'three': (5, 12, (3, 9, 6)),
        'five': (4, 9, (5, 2, 4, 5, 5, 3, 9)),
        'mixed': (6, 12, tuple(range(2, 10))),
    }
    names = list(profiles)
    guard = 0
    while len(eqs) < n and guard < 200000:
        guard += 1
        tag = rng.choice(names)
        lo, hi, pool = profiles[tag]
        q = rng.randint(lo, hi)
        k = rng.randint(1, min(4, len(set(pool)))) if tag not in ('tiny', 'mid') else len(set(pool))
        sub = rng.sample(sorted(set(pool)), k)
        M = [rng.choice(sub) for _ in range(q)]
        if npat(M) > cap:
            continue
        add(M, tag)
    return eqs


def plants(heavy=False, per_len=4, cap=2e8, seed=7):
    rng = random.Random(seed)
    rows = []
    for a in range(0, 130):
        for b in range(0, 80):
            for c in range(0, 50):
                y = 2 ** a * 3 ** b * 7 ** c
                if y < 10 or y >= 10 ** 40:
                    continue
                s = str(y)
                if '0' in s:
                    continue
                M = tuple(sorted(int(ch) for ch in s if ch != '1'))
                if len(M) < 1:
                    continue
                rows.append(dict(y=y, n=len(s), a=a, b=b, c=c, M=list(M), npat=npat(M)))
    lim = 1e9 if heavy else cap
    rows = [r for r in rows if r['npat'] <= lim]
    chosen = []
    for L in range(2, 15):
        pool = [r for r in rows if r['n'] == L]
        pool.sort(key=lambda r: r['npat'])
        want = per_len if L <= 9 else 2
        if L >= 12:
            want = 2 if L == 12 else 1
        if L == 13 and not heavy:
            continue
        if len(pool) <= want:
            chosen += pool
        else:
            idx = sorted(rng.sample(range(len(pool)), want))
            chosen += [pool[i] for i in idx]
    for r in chosen:
        sp = 1
        for d in r['M']:
            sp *= d
        r['s'] = sp
    chosen.sort(key=lambda r: r['npat'])
    return chosen


def synth_cfgs(work, base_cfgp):
    """Off-nominal level-12 configs derived from a real one: per-a K row replaced (K != 3), and np = 7 (two duplicate zero-filter primes)."""
    out = []
    lines = open(base_cfgp).read().rstrip('\n').split('\n')
    A = int(lines[0].split()[1])
    nm = os.path.basename(base_cfgp)
    for tag, K in (('k0', 0), ('k1', 1), ('k2', 2), ('k4', 4), ('k6', 6), ('k19', 19), ('kmix', None)):
        row = ' '.join(str(K if K is not None else (0, 1, 2, 3, 4, 5, 19)[i % 7]) for i in range(A + 1))
        p = os.path.join(work, 'cfg', f'synth_{tag}_{nm}')
        open(p, 'w').write('\n'.join(lines[:-1] + [row]) + '\n')
        out.append((tag, p))
    np0 = int(lines[2])
    last = lines[3 + 4 * (np0 - 1): 3 + 4 * np0]
    new = lines[:2] + [str(np0 + 2)] + lines[3: 3 + 4 * np0] + last + last + lines[3 + 4 * np0:]
    p = os.path.join(work, 'cfg', f'synth_np7_{nm}')
    open(p, 'w').write('\n'.join(new) + '\n')
    out.append(('np7', p))
    return out


def fast_subset(corpus, n=110, cap=2_000_000):
    rng = random.Random(1)
    tags = sorted({e['tag'] for e in corpus})
    out = []
    per = max(5, n // len(tags))
    for t in tags:
        pool = [e for e in corpus if e['tag'] == t and e['npat'] <= cap]
        rng.shuffle(pool)
        out += pool[:per]
    return out[:n + 20]


def fast_plants(pl):
    out = []
    for L in range(2, 12):
        out += sorted([p for p in pl if p['n'] == L], key=lambda p: p['npat'])[:2]
    out += sorted([p for p in pl if p['n'] == 12], key=lambda p: p['npat'])[:1]
    return out


def small_units(maxn=6):
    rows = []
    for a in range(0, 40):
        for b in range(0, 30):
            for c in range(0, 20):
                y = 2 ** a * 3 ** b * 7 ** c
                if y < 2 or y >= 10 ** maxn:
                    continue
                s = str(y)
                if '0' in s:
                    continue
                M = sorted(int(ch) for ch in s if ch != '1')
                if not M:
                    continue
                rows.append(dict(y=y, n=len(s), a=a, b=b, c=c, M=M))
    rows.sort(key=lambda r: r['y'])
    return rows


def synthN_inputs(work, genuine, per_n=3, ns=(5, 6, 7, 8, 9)):
    """Level-24 lvlN inputs: a genuine parent whose digit count n equals a replaced K row (K = n != 4).
    The tail test then runs on an n-digit window, which has an internal zero often enough to exercise the exact-loop zero check."""
    import gv_stages as S
    out = []
    for n in ns:
        pool = [g for g in genuine if g['n'] == n][:per_n]
        for g in pool:
            M = tuple(sorted(g['M']))
            cfgp, info = exportN(work, M, 24)
            lines = open(cfgp).read().rstrip('\n').split('\n')
            A = int(lines[0].split()[2])
            lines[-1] = ' '.join([str(n)] * (A + 1))
            p = os.path.join(work, 'cfg', f'synthN_k{n}_{os.path.basename(cfgp)}')
            open(p, 'w').write('\n'.join(lines) + '\n')
            body, _ = S.genuine_parent(g['y'], M, 12)
            tok = body.split()
            uo = info['U_old']
            tok[-2] = str(int(tok[-2]) + uo[0][0])
            tok[-1] = str(int(tok[-1]) + uo[0][1])
            body = ' '.join(tok) + '\n'
            pp = os.path.join(work, 'par', f"synthN_{g['y']}.txt")
            os.makedirs(os.path.dirname(pp), exist_ok=True)
            open(pp, 'w').write(body)
            out.append(dict(kernel='lvlN', args=[p, pp], tag=f"K{n}_y{g['y']}"))
    return out
