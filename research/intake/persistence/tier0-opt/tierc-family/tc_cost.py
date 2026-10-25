import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, time, json, math
from famlib import *
from famtest import *
from tc_dp import count_zero_sum, P


class PD:
    def __init__(self, p, g, l2, l3, l7, facs):
        self.p, self.g, self.l2, self.l3, self.l7, self.facs = p, g, l2, l3, l7, facs
        self.tabs = {}
        for q, e in facs:
            gq = pow(g, (p - 1) // q, p)
            m = math.isqrt(q) + 1
            baby = {}
            cur = 1
            for j in range(m):
                baby.setdefault(cur, j)
                cur = cur * gq % p
            self.tabs[q] = (baby, m, pow(gq, -m, p))

    def dlog(self, r):
        p, g = self.p, self.g
        rems = []
        mods = []
        for q, e in self.facs:
            qe = q ** e
            gam = pow(g, (p - 1) // q, p)
            x = 0
            hq = pow(r, (p - 1) // qe, p)
            ginv = pow(g, -1, p)
            baby, m, step = self.tabs[q]
            for i in range(e):
                t = pow(hq * pow(ginv, x * (p - 1) // qe, p) % p, (p - 1) // q ** (i + 1) * 1, p) if False else None
                base = pow(g, (p - 1) // qe, p)
                cur = hq * pow(base, -x, p) % p
                cur = pow(cur, q ** (e - 1 - i), p)
                gg = 1
                found = None
                z = cur
                for j in range(m + 1):
                    if z in baby:
                        found = (baby[z] + j * m) % q
                        break
                    z = z * step % p
                assert found is not None
                x += found * q ** i
            rems.append(x)
            mods.append(qe)
        x = 0
        M = 1
        for r_i, m_i in zip(rems, mods):
            t = ((r_i - x) * pow(M, -1, m_i)) % m_i
            x += M * t
            M *= m_i
        assert pow(g, x, p) == r % p
        return x


def read_level192():
    out = []
    for line in open(DATA + 'levelprimes.txt'):
        if line.startswith('#') or not line.strip():
            continue
        t = line.split()
        if int(t[0]) != 192:
            continue
        p, g, l2, l3, l7, nf = int(t[1]), int(t[2]), int(t[3]), int(t[4]), int(t[5]), int(t[6])
        facs = [(int(t[7 + 2 * i]), int(t[8 + 2 * i])) for i in range(nf)]
        out.append(PD(p, g, l2, l3, l7, facs))
    return out


def child_alive(co0, a, V, pds):
    co = co0
    for pd in pds:
        r = V % pd.p
        if r == 0:
            return False
        lr = pd.dlog(r)
        co = co.cong(pd.l3, pd.l7, (lr - a * pd.l2) % (pd.p - 1), pd.p - 1)
        if co is None:
            return False
    return True


if __name__ == '__main__':
    t0 = time.time()
    rng = random.Random(5)
    lam = build_lambdas()
    pds = read_level192()
    y = 330812181
    f = factor237(y)
    co0 = Coset((f[1], f[2]), lam[96])
    for pd in pds:
        for _ in range(20):
            r = rng.randrange(1, pd.p)
            pd.dlog(r)
    tt = []
    alive = 0
    for _ in range(300):
        V = rng.randrange(10 ** 95, 10 ** 96)
        t1 = time.perf_counter()
        alive += child_alive(co0, 0, V, pds)
        tt.append(time.perf_counter() - t1)
    t_cand = sum(tt) / len(tt)
    print('child test at the seven level-192 primes: mean seconds', t_cand, 'n', len(tt), 'alive', alive, 'primes', [pd.p for pd in pds])
    f_t = []
    a0 = 0
    for _ in range(2000):
        W = rng.randrange(10 ** 90, 10 ** 96)
        t1 = time.perf_counter()
        alive_from_W(a0, y, W, 384)
        f_t.append(time.perf_counter() - t1)
    t_fam = sum(f_t) / len(f_t)
    print('family shadow test (one congruence) mean seconds', t_fam)
    lamL = lam
    ref_t = []
    for _ in range(40):
        sm = rng.randrange(1, 10 ** 8)
        t1 = time.perf_counter()
        for L in (96, 192, 384, 480):
            ref_alive(a0, y, R(L) + sm, L, lamL)
        ref_t.append(time.perf_counter() - t1)
    t_shadow_ref = sum(ref_t) / len(ref_t)
    print('reference lattice shadow test over 96/192/384/480: mean seconds', t_shadow_ref)

    sets = [
        ('C 128421199872 k=31', [2] * 23 + [3] * 7 + [7]),
        ('C 3416267673274176 k=34', [2] * 6 + [3] * 27 + [7]),
        ('C 727326941773824 k=44', [2] * 39 + [3] * 3 + [7] * 2),
    ]
    rows = []
    for tag, M in sets:
        k = len(M)
        for nfixed in (4, 8):
            r = k - nfixed
            for _ in range(8):
                Mu = rng.sample(M, r)
                pos = [(d, rng.randrange(0, 96)) for d in Mu]
                nu = rng.randrange(0, 96)
                t1 = time.perf_counter()
                cnt = count_zero_sum(pos, nu)
                t_dp = time.perf_counter() - t1
                ncand = cnt[0] - 1
                per_ref = t_dp + ncand * t_cand + t_shadow_ref
                per_fam = t_dp + ncand * t_cand + t_fam
                rows.append(dict(tag=tag, k=k, r=r, ncand=ncand, expected=2 ** (r + 1) / P, t_dp=t_dp, ratio=per_ref / per_fam))
            sub = [x for x in rows if x['tag'] == tag and x['r'] == r]
            nc = [x['ncand'] for x in sub]
            rt = [x['ratio'] for x in sub]
            print(json.dumps(dict(tag=tag, k=k, unplaced_r=r, expected_children=round(2 ** (r + 1) / P, 2), measured_mean=round(sum(nc) / len(nc), 2), measured_min=min(nc), measured_max=max(nc), t_dp_mean=round(sum(x['t_dp'] for x in sub) / len(sub), 3), ratio_mean=sum(rt) / len(rt), ratio_min=min(rt), ratio_max=max(rt))), flush=True)
    json.dump(dict(t_cand=t_cand, t_fam=t_fam, t_shadow_ref=t_shadow_ref, rows=rows), open(OUT + 'tc_cost.json', 'w'))
    print('seconds', round(time.time() - t0, 1))
