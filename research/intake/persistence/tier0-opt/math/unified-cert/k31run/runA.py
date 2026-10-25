import sys, os, json, time, random, argparse, signal, hashlib

sys.dont_write_bytecode = True
RUNDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(RUNDIR))

from ucert.env import *
from ucert import cert_dual, planted as PL
from ucert.tierc import tierc_pattern, U_from_log10

E_NODES = 3
EXPECT_TOTAL = 440640
EXPECT_FAMILIES = [93312, 46656, 93312, 82944, 41472, 82944]
UTABLE = os.path.join(RUNDIR, 'utable_u2_k31.txt')


NODE_CACHE = os.environ.get('K31_NODE_CACHE')


def enumerate_nodes():
    import pickle
    if NODE_CACHE and os.path.exists(NODE_CACHE):
        with open(NODE_CACHE, 'rb') as f:
            return pickle.load(f)
    from ucert import cert_cvp
    pat = tierc_pattern()
    nodes = cert_cvp.expand_nodes(pat, pat['reps'][0], E_NODES)
    if NODE_CACHE:
        with open(NODE_CACHE, 'wb') as f:
            pickle.dump(nodes, f, protocol=4)
    return nodes


def family_counts(nodes):
    order, cnt = [], {}
    for n in nodes:
        k = int(n['Y']) % 10 ** LMAX
        if k not in cnt:
            cnt[k] = 0
            order.append(k)
        cnt[k] += 1
    return [cnt[k] for k in order]


def gate_check(total, fams, exp_total, exp_fams):
    problems = []
    if total != exp_total:
        problems.append('node count %d != expected %d' % (total, exp_total))
    if fams != exp_fams:
        if sorted(fams) != sorted(exp_fams):
            problems.append('family counts %s != expected %s (as multisets)' % (fams, exp_fams))
        else:
            problems.append('family counts match as a multiset but order differs: %s vs %s' % (fams, exp_fams))
    return problems


def gate_eval(nodes, exp_total, exp_fams):
    total = len(nodes)
    fams = family_counts(nodes)
    digests = sorted(node_digest(n) for n in nodes)
    info = {'total': total, 'families_first_appearance': fams, 'families_sorted': sorted(fams), 'sum_families': sum(fams),
            'distinct_digests': len(set(digests)), 'digest_list_sha256': hashlib.sha256('\n'.join(digests).encode()).hexdigest()}
    problems = gate_check(total, fams, exp_total, exp_fams)
    ordered_ok = fams == exp_fams
    sorted_ok = sorted(fams) == sorted(exp_fams)
    info['ordered_match'] = ordered_ok
    info['multiset_match'] = sorted_ok
    info['distinct_equals_total'] = info['distinct_digests'] == total
    if not info['distinct_equals_total']:
        problems.append('duplicate node digests: %d distinct of %d' % (info['distinct_digests'], total))
    return info, problems


def cmd_gate(args):
    t0 = time.time()
    nodes = enumerate_nodes()
    info, problems = gate_eval(nodes, args.expect_total, args.expect_families)
    info['seconds'] = round(time.time() - t0, 1)
    print(json.dumps(info, sort_keys=True), flush=True)
    if problems:
        print('GATE REFUSED: ' + '; '.join(problems), flush=True)
        sys.exit(1)
    print('GATE PASSED: N_3 = %d, families %s' % (info['total'], info['families_first_appearance']), flush=True)


def load_done(path):
    done = set()
    if os.path.exists(path):
        for l in open(path):
            l = l.strip()
            if not l:
                continue
            try:
                done.add(json.loads(l)['node'])
            except Exception:
                pass
    return done


def rec_hash(rec):
    return sha({k: v for k, v in rec.items() if k != 't'})


def system_size(node, D):
    from collections import Counter
    types = Counter(tuple(x) for x in node['remaining'])
    return len(types) * (D - node['s'] // LMAX)


class Timeout(Exception):
    pass


def _alarm(*a):
    raise Timeout('timeout')


def certify_one(node, D, rho2, cap, timeout, verify):
    t0 = time.time()
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(timeout)
    try:
        rec = cert_dual.certify_node(node, D, rho2, node_cap=cap)
        verdict = 'certified' if rec['certified'] else ('refused-cap' if rec.get('cap_hit') else 'refused')
        err = None
    except Exception as ex:
        rec, verdict, err = None, 'error', repr(ex)[:200]
    finally:
        signal.alarm(0)
    t = time.time() - t0
    out = {'verdict': verdict, 'size': system_size(node, D), 't': round(t, 4)}
    if err:
        out['error'] = err
    if rec is not None:
        out['rec_hash'] = rec_hash(rec)
        out['kind'] = rec.get('kind')
        out['nodes_visited'] = rec.get('stats', {}).get('nodes') if isinstance(rec.get('stats'), dict) else None
        out['M_bits'] = len(rec['M']) * 3322 // 1000 if rec.get('M') else None
        if rec['certified']:
            if verify:
                t1 = time.time()
                try:
                    out['verified'] = bool(cert_dual.verify_record(node, rec, rho2))
                except Exception as ex:
                    out['verified'] = False
                    out['verify_error'] = repr(ex)[:200]
                out['t_verify'] = round(time.time() - t1, 4)
            else:
                out['verified'] = None
    return out


def select_indices(n, args):
    idx = list(range(n))
    if args.sample:
        idx = sorted(random.Random(args.seed).sample(idx, args.sample))
    idx = idx[args.start:]
    if args.limit:
        idx = idx[:args.limit]
    return idx


def cmd_run(args, nodes=None):
    U = load_utable(args.utable)[(31, 0)]
    rho2 = disc_radius2(U)
    t0 = time.time()
    nodes = nodes if nodes is not None else enumerate_nodes()
    print('enumerated %d nodes in %.1fs' % (len(nodes), time.time() - t0), flush=True)
    if len(nodes) != EXPECT_TOTAL:
        print('REFUSED: node count %d != %d' % (len(nodes), EXPECT_TOTAL), flush=True)
        sys.exit(1)
    idx = select_indices(len(nodes), args)
    done = load_done(args.out)
    print('selected %d, already done %d' % (len(idx), len(done)), flush=True)
    cnt = {}
    tstart = time.time()
    processed = 0
    with open(args.out, 'a') as fo:
        for n_i, i in enumerate(idx):
            node = nodes[i]
            dg = node_digest(node)
            if dg in done:
                continue
            ver = args.verify_every > 0 and (processed % args.verify_every == 0)
            res = certify_one(node, args.D, rho2, args.node_cap, args.timeout, ver)
            row = {'idx': i, 'node': dg, 'D': args.D}
            row.update(res)
            fo.write(json.dumps(row, sort_keys=True) + '\n')
            fo.flush()
            processed += 1
            cnt[res['verdict']] = cnt.get(res['verdict'], 0) + 1
            if res.get('verified') is False:
                cnt['verify_FAILED'] = cnt.get('verify_FAILED', 0) + 1
            if processed % args.progress == 0:
                el = time.time() - tstart
                print('processed %d/%d elapsed %.0fs %s' % (processed, len(idx) - len(done), el, cnt), flush=True)
    print('DONE processed %d %s elapsed %.0fs' % (processed, cnt, time.time() - tstart), flush=True)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def cmd_summary(args):
    rows = [json.loads(l) for l in open(args.out) if l.strip()]
    v = {}
    for r in rows:
        v[r['verdict']] = v.get(r['verdict'], 0) + 1
    ts = [r['t'] for r in rows]
    tv = [r['t_verify'] for r in rows if 't_verify' in r]
    ver = [r['verified'] for r in rows if r.get('verified') is not None]
    out = {'rows': len(rows), 'verdicts': v, 'mean_t': sum(ts) / len(ts), 'p50_t': pct(ts, .5), 'p95_t': pct(ts, .95), 'max_t': max(ts),
           'sum_t': sum(ts), 'verified_true': sum(1 for x in ver if x), 'verified_false': sum(1 for x in ver if not x),
           'mean_t_verify': (sum(tv) / len(tv)) if tv else None,
           'sizes': [min(r['size'] for r in rows), max(r['size'] for r in rows)]}
    out['projected_core_hours_A_only'] = out['mean_t'] * EXPECT_TOTAL / 3600
    if tv:
        out['projected_core_hours_A_plus_verify_all'] = (out['mean_t'] + out['mean_t_verify']) * EXPECT_TOTAL / 3600
    print(json.dumps(out, sort_keys=True))


def cmd_planted(args, nodes=None):
    U = load_utable(args.utable)[(31, 0)]
    nodes = nodes if nodes is not None else enumerate_nodes()
    rng = random.Random(args.seed)
    pick = sorted(rng.sample(range(len(nodes)), args.nodes))
    per = -(-args.words // args.nodes)
    D = args.D
    total, certified, refused = 0, 0, 0
    with open(args.out, 'a') as fo:
        for i in pick:
            node = nodes[i]
            vars_, types = PL.high_vars(node, D)
            got = 0
            tries = 0
            while got < per and total < args.words and tries < 50:
                tries += 1
                for w in PL.random_words(vars_, types, rng, per - got):
                    sn = PL.sub_nearest(node, D, w)
                    if sn is None:
                        continue
                    nn, pt, L = sn
                    assert PL.exact_unit_ok(0, pt, L, LMAX * D)
                    rec = cert_dual.certify_node(node, D, nn, node_cap=args.node_cap)
                    c = bool(rec['certified'])
                    total += 1
                    got += 1
                    certified += c
                    refused += (not c)
                    fo.write(json.dumps({'kind': 'k31-planted', 'idx': i, 'node': node_digest(node), 'D': D, 'word_size': len(w),
                                         'rho2_digits': len(str(nn)), 'certified': c, 'cap_hit': bool(rec.get('cap_hit'))}, sort_keys=True) + '\n')
                    fo.flush()
                    if got >= per or total >= args.words:
                        break
            print('node idx %d words %d total %d certified %d' % (i, got, total, certified), flush=True)
    print('PLANTED words=%d refused=%d certified=%d nodes=%d' % (total, refused, certified, len(pick)), flush=True)
    if certified or total < args.words:
        print('PLANTED GATE FAILED', flush=True)
        sys.exit(1)
    print('PLANTED GATE PASSED: every planted word refused', flush=True)


def cmd_margins(args, nodes=None):
    ut = load_utable(args.utable)[(31, 0)]
    nodes = nodes if nodes is not None else enumerate_nodes()
    rng = random.Random(args.seed)
    pick = sorted(rng.sample(range(len(nodes)), args.nodes))
    cells = [(5, 246.0183, ut), (5, 255.0, None), (5, 265.0, None), (5, 275.0, None), (5, 281.51, None), (6, 281.51, None)]
    summary = {}
    with open(args.out, 'a') as fo:
        for i in pick:
            node = nodes[i]
            dg = node_digest(node)
            row = {'idx': i, 'node': dg, 'cells': {}}
            best = None
            for D, lg, U in cells:
                U = U if U is not None else U_from_log10(lg)
                res = certify_one(node, D, disc_radius2(U), args.node_cap, args.timeout, False)
                key = 'D%d@%s' % (D, lg)
                row['cells'][key] = res['verdict']
                summary.setdefault(key, {}).setdefault(res['verdict'], 0)
                summary[key][res['verdict']] += 1
                if D == 5 and res['verdict'] == 'certified':
                    best = lg
            row['largest_D5_ceiling_certified'] = best
            fo.write(json.dumps(row, sort_keys=True) + '\n')
            fo.flush()
    print('MARGINS', json.dumps(summary, sort_keys=True), flush=True)


def cmd_smoke(args):
    t0 = time.time()
    nodes = enumerate_nodes()
    print('enumerated in %.1fs' % (time.time() - t0), flush=True)
    info, problems = gate_eval(nodes, EXPECT_TOTAL, EXPECT_FAMILIES)
    print('gate real:', 'REFUSED ' + '; '.join(problems) if problems else 'PASSED', flush=True)
    bad_fams = list(EXPECT_FAMILIES)
    bad_fams[3] += 1
    for label, et, ef in (('total+1', EXPECT_TOTAL + 1, EXPECT_FAMILIES), ('family[3]+1', EXPECT_TOTAL, bad_fams)):
        _, pr = gate_eval(nodes, et, ef)
        print('gate planted negative (%s): %s' % (label, 'GATE REFUSED: ' + '; '.join(pr) if pr else 'NOT REFUSED (gate is broken)'), flush=True)
    d = args.dir
    base = dict(utable=UTABLE, D=5, node_cap=400, timeout=600, seed=args.seed)
    run_a = argparse.Namespace(out=os.path.join(d, 'smoke_A.jsonl'), start=0, limit=args.limit, sample=0, verify_every=1, progress=50, **base)
    cmd_run(run_a, nodes)
    cmd_summary(argparse.Namespace(out=run_a.out))
    cmd_planted(argparse.Namespace(out=os.path.join(d, 'smoke_planted.jsonl'), nodes=args.pl_nodes, words=args.pl_words, **base), nodes)
    cmd_margins(argparse.Namespace(out=os.path.join(d, 'smoke_margins.jsonl'), nodes=args.mg_nodes, **base), nodes)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gate')
    g.add_argument('--expect-total', type=int, default=EXPECT_TOTAL)
    g.add_argument('--expect-families', type=int, nargs='+', default=EXPECT_FAMILIES)
    sm = sp.add_parser('smoke')
    sm.add_argument('--dir', default=RUNDIR)
    sm.add_argument('--limit', type=int, default=200)
    sm.add_argument('--pl-nodes', type=int, default=10)
    sm.add_argument('--pl-words', type=int, default=60)
    sm.add_argument('--mg-nodes', type=int, default=20)
    sm.add_argument('--seed', type=int, default=1)
    for name in ('run', 'planted', 'margins', 'summary'):
        p = sp.add_parser(name)
        p.add_argument('--out', required=True)
        p.add_argument('--utable', default=UTABLE)
        p.add_argument('--D', type=int, default=5)
        p.add_argument('--node-cap', type=int, default=400)
        p.add_argument('--timeout', type=int, default=600)
        p.add_argument('--seed', type=int, default=1)
        if name == 'run':
            p.add_argument('--start', type=int, default=0)
            p.add_argument('--limit', type=int, default=0)
            p.add_argument('--sample', type=int, default=0)
            p.add_argument('--verify-every', type=int, default=1)
            p.add_argument('--progress', type=int, default=1000)
        if name == 'planted':
            p.add_argument('--nodes', type=int, default=50)
            p.add_argument('--words', type=int, default=500)
        if name == 'margins':
            p.add_argument('--nodes', type=int, default=200)
    args = ap.parse_args()
    {'gate': cmd_gate, 'run': cmd_run, 'planted': cmd_planted, 'margins': cmd_margins, 'summary': cmd_summary, 'smoke': cmd_smoke}[args.cmd](args)


if __name__ == '__main__':
    main()
