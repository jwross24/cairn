import sys, os, json, math, random, time
from decimal import Decimal, getcontext
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
getcontext().prec = 60
from n1lib import *
from n1tier import *
from n1cert import *
from n1solve import valid_x
import n1diff as ND
from n1scale import tierc_setup, sample_base, system_for, U_from_log10

FROZEN = ND.FROZEN


def log10i(n):
    return log10_big(abs(n)) if n else 0.0


def info_budget(sysd, rho2):
    zb = z_box(sysd['co'], rho2)
    w = [max(1, zb[0][1] - zb[0][0]), max(1, zb[1][1] - zb[1][0])]
    groups = defaultdict(list)
    for (d, e, t) in sysd['vars']:
        groups[(e, t)].append(1)
    g = len(groups)
    npr = g + 2
    logM = log10i(sysd['M'])
    need = log10i(w[0]) + log10i(w[1]) + (g + 2) * math.log10(npr)
    return dict(logM=logM, logZ1=log10i(w[0]), logZ2=log10i(w[1]), groups=g, vars=len(sysd['vars']), predicted_slack=logM - need)


def random_admissible_x(sysd, types_rem, E, D, rng):
    """random admissible placement of the free digits into blocks E..D-1 (unlabeled, per-block per-class choice)."""
    x = {}
    rem = Counter(types_rem)
    for t in range(E, D):
        ch = rng.choice(list(block_choices(rem)))
        for (d, e) in ch:
            x[(d, e, t)] = 1
            rem[(d, e)] -= 1
    return [1 if x.get(v) else 0 for v in sysd['vars']]


def exact_nn_for_x(sysd, a, x):
    L = target_value(sysd['Tbase'], sysd['vars'], x, sysd['K'])
    Lfull = sysd['Tbase']
    for (d, e, t), xi in zip(sysd['vars'], x):
        if xi:
            Lfull += (d - 1) * 10 ** (e + LMAX * t)
    c2 = cut_coset(sysd['co'], a, Lfull, sysd['K'])
    return DC.nearest_norm(c2)[0]


if __name__ == '__main__':
    mode = sys.argv[1]
    E = int(sys.argv[2])
    ns = int(sys.argv[3])
    logU = float(sys.argv[4]) if len(sys.argv) > 4 else 281.51
    extra = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    seed = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    node_cap = int(os.environ.get('N1_NODECAP', '200'))
    D = int(os.environ.get('N1_D', str(2 * E)))
    rng = random.Random(seed)
    co0, a, types = tierc_setup()
    s1 = json.load(open(os.path.join(FROZEN, 'tierc_surv1.json')))
    surv1 = [(tuple(map(tuple, ch)), Coset(tuple(v0), tuple(u1), tuple(u2))) for ch, v0, u1, u2 in s1]
    extra_types = None
    if extra:
        extra_types = Counter()
        classes = list(range(10))
        for i in range(extra):
            e = classes[i % 10]
            extra_types[(2 if i < 10 else 3, e)] += 1
    U = U_from_log10(logU)
    rho2 = disc_radius2(U)
    bkz = int(os.environ.get('N1_BKZ', '0'))
    worst = []
    if mode == 'certworst':
        for ch, co1 in surv1:
            placed = {0: ch}
            co = co1
            for t in range(1, E):
                placed[t] = []
                co = cut_coset(co, a, Lfor(placed, LMAX * (t + 1)), LMAX * (t + 1))
            worst.append((placed, co))
        ns = len(worst)
    for i in range(ns):
        t0 = time.time()
        if mode == 'certworst':
            placed, co = worst[i]
        else:
            placed, co = sample_base(co0, a, types, E, rng, surv1)
        t_base = time.time() - t0
        sysd = system_for(co, placed, a, types, E, D, extra_types)
        bud = info_budget(sysd, rho2)
        row = dict(mode=mode, E=E, D=D, logU=logU, extra=extra, t_base=round(t_base, 1), exact=sysd['exact'], **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in bud.items()})
        if mode in ('cert', 'certworst'):
            t1 = time.time()
            st = {'nodes': 0, 'certs': 0, 'max_depth': 0}
            res, st = certify_branching(sysd, rho2, node_cap=node_cap, stats=st, bkz=bkz)
            row.update(certified=res, nodes=st['nodes'], depth=st['max_depth'], t_cert=round(time.time() - t1, 2))
        elif mode == 'plant':
            tt = Counter(types)
            if extra_types:
                tt.update(extra_types)
            rem = tinsert(tt, [x for lst in placed.values() for x in lst])
            x = random_admissible_x(sysd, rem, E, D, rng)
            t1 = time.time()
            nn = exact_nn_for_x(sysd, a, x)
            row.update(t_exact_cut=round(time.time() - t1, 1), nn_digits=len(str(nn)))
            for name, r2 in (('at_nn', nn), ('nn_over_1e12', nn // 10 ** 12)):
                st = {'nodes': 0, 'certs': 0, 'max_depth': 0}
                res, st = certify_branching(sysd, r2, node_cap=node_cap, stats=st)
                row[name] = res
                row[name + '_nodes'] = st['nodes']
        print(json.dumps(row), flush=True)
