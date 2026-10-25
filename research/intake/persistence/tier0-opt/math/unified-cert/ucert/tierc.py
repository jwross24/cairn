import sys, os, json, time, random, argparse, signal
from decimal import Decimal, getcontext
from .env import *
from . import cert_dual, cert_cvp

getcontext().prec = 60

TIERC_CLASSES = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2,
                 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}


def tierc_pattern():
    De = sorted((d, e) for e, l in TIERC_CLASSES.items() for d in l)
    lam = json.load(open(os.path.join(ROOT, 'inputs', 'lam96.json')))
    y = 3 ** 3 * 7 ** 10
    return {'format': 'ucert-pattern-v1', 'id': 'tierc k31 3^3 7^10', 'a': 0, 'b': 3, 'c': 10, 'y': y, 'k': len(De),
            'reps': [{'nu': 2, 'De': [list(x) for x in De]}], 'lam': lam}


def U_from_log10(x):
    return int(Decimal(10) ** Decimal(str(x)))


def sample_node(pattern, rep, E, rng, first_lin=12, p_none=0.0):
    a = pattern['a']
    lam = coset_from_json(pattern['lam'])
    co = Coset((pattern['b'], pattern['c']), lam.u1, lam.u2)
    De = [tuple(x) for x in rep['De']]
    s = LMAX * E
    classes = {e % LMAX for _, e in De}
    mc, mf, Y = 0, 0, 0
    remaining = list(range(len(De)))
    while True:
        if mf >= 3 and mf > mc:
            if Y % 5 == 0 or (mf > a and v2(Y % 10 ** mf) != a):
                return None
            co = cert_cvp.extend_exact(co, a, mc, Y, mf) if (mc >= first_lin and mc - a >= 1) else cut_coset(co, a, Y, mf)
            if co is None:
                return None
            mc = mf
        if mf >= s:
            break
        p = mf
        while p < s and p % LMAX not in classes:
            p += 1
        if p >= s:
            Y += (10 ** s - 10 ** mf) // 9
            mf = s
            continue
        opts = [None]
        seen = set()
        for j in remaining:
            if De[j][1] % LMAX == p % LMAX and De[j][0] not in seen:
                seen.add(De[j][0])
                opts.append(j)
        j = None if (p >= LMAX and rng.random() < p_none) else rng.choice(opts)
        Y += (10 ** (p + 1) - 10 ** mf) // 9 + ((De[j][0] - 1) * 10 ** p if j is not None else 0)
        mf = p + 1
        if j is not None:
            remaining.remove(j)
    return {'format': 'ucert-node-v1', 'a': a, 's': s, 'Y': str(Y % 10 ** s), 'coset': coset_to_json(co),
            'remaining': sorted([list(De[j]) for j in remaining])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=6)
    ap.add_argument('--E', type=int, default=3)
    ap.add_argument('--D', type=int, nargs='+', default=[5, 6])
    ap.add_argument('--log10U', type=float, nargs='+', default=[281.51])
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--min', action='store_true')
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--p_none', type=float, default=0.0)
    ap.add_argument('--planted', type=int, default=0)
    ap.add_argument('--backends', nargs='+', default=['dual', 'cvp'])
    args = ap.parse_args()
    rng = random.Random(args.seed)
    pat = tierc_pattern()
    rep = pat['reps'][0]
    with open(args.out, 'a') as fo:
        got = 0
        while got < args.n:
            t0 = time.time()
            node = sample_node(pat, rep, args.E, rng, p_none=args.p_none)
            if node is None:
                continue
            t_node = time.time() - t0
            got += 1
            if args.planted:
                from . import planted as PL
                for D in args.D:
                    if exact_E(D, 0) != args.E:
                        continue
                    vars_, types = PL.high_vars(node, D)
                    for w in [[]] + PL.random_words(vars_, types, rng, args.planted):
                        sn = PL.sub_nearest(node, D, w)
                        if sn is None:
                            continue
                        nn, pt, L = sn
                        assert PL.exact_unit_ok(0, pt, L, LMAX * D)
                        ca, cb, okpt, rb = PL.refusal(node, node, D, nn)
                        row = {'kind': 'tierc-planted', 'node': node_digest(node), 'D': D, 'word_size': len(w), 'rho2_digits': len(str(nn)),
                               'dual_certified': ca, 'cvp_certified': cb, 'cvp_point_ok': okpt, 'ok': (not ca) and (not cb) and okpt is True}
                        fo.write(json.dumps(row, sort_keys=True) + '\n')
                        fo.flush()
                        print(row, flush=True)
                continue
            for D in args.D:
                if exact_E(D, 0) != args.E:
                    continue
                for lg in args.log10U:
                    rho2 = disc_radius2(U_from_log10(lg))
                    row = {'kind': 'tierc-sample', 'node': node_digest(node), 'E': args.E, 'D': D, 'log10U': lg, 'remaining': len(node['remaining']),
                           't_node': round(t_node, 3)}
                    for name, mod in (('dual', cert_dual), ('cvp', cert_cvp)):
                        if name not in args.backends:
                            continue
                        t1 = time.time()
                        signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError('timeout')))
                        signal.alarm(args.timeout)
                        try:
                            rec = mod.certify_node(node, D, rho2) if name == 'cvp' else mod.certify_node(node, D, rho2, node_cap=400)
                            row[name] = {'certified': rec['certified'], 't': round(time.time() - t1, 3), 'dim': rec.get('dim'), 'nodes': rec.get('nodes', rec.get('stats', {}).get('nodes'))}
                            if rec['certified']:
                                t2 = time.time()
                                row[name]['verified'] = mod.verify_record(node, rec, rho2)
                                row[name]['t_verify'] = round(time.time() - t2, 3)
                        except Exception as ex:
                            row[name] = {'error': repr(ex)[:200], 't': round(time.time() - t1, 3)}
                        finally:
                            signal.alarm(0)
                    fo.write(json.dumps(row, sort_keys=True) + '\n')
                    fo.flush()
                    print(row, flush=True)


if __name__ == '__main__':
    main()
