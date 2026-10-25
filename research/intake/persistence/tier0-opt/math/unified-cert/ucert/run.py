import sys, os, json, time, argparse
from collections import Counter
from .env import *
from . import cert_dual, cert_cvp

BACKENDS = {'dual': cert_dual, 'cvp': cert_cvp}


def load_patterns(path):
    return [json.loads(l) for l in open(path)]


def load_oracle(path):
    out = {}
    for l in open(path):
        f = l.rstrip('\n').split('\t')
        fk = f[0]
        ri, D, res, cases, stats, nn = int(f[5]), int(f[6]), f[7], int(f[8]), f[9], f[10]
        out.setdefault(fk, {}).setdefault(ri, {})[D] = (res, stats, None if nn == '-' else int(nn))
    return out


def node_canon(node):
    co = coset_from_json(node['coset'])
    return (node['Y'], tuple(map(tuple, node['remaining'])), co.index(), co.contains(*co.v0))


def node_set_key(node):
    return (node['Y'], tuple(map(tuple, node['remaining'])))


def run_rep(pattern, ri, rep, backend, maxD, with_min, verify, log, nice_cache, minmaxD=99):
    mod = BACKENDS[backend]
    a = pattern['a']
    U = pattern['U']
    rho2 = disc_radius2(U)
    rows = []
    for D in range(1, maxD + 1):
        E = exact_E(D, a)
        ck = (backend, pattern['id'], ri, E)
        if ck not in nice_cache:
            t0 = time.time()
            nice_cache[ck] = (mod.expand_nodes(pattern, rep, E), time.time() - t0)
        nodes, t_exp = nice_cache[ck]
        row = {'pattern': pattern['id'], 'rep': ri, 'D': D, 'E': E, 'backend': backend, 'nodes': len(nodes), 'node_digests': sorted(node_digest(n) for n in nodes), 'rho2': str(rho2), 't_expand': round(t_exp, 3)}
        if not nodes:
            row.update(status='CLOSED-cut', certified_nodes=0)
            rows.append(row)
            log(row)
            break
        ncert = 0
        nver = 0
        t0 = time.time()
        recs = []
        minnn = None
        mincomplete = True
        labeled = 0
        for node in nodes:
            rec = mod.certify_node(node, D, rho2)
            if rec['certified']:
                ncert += 1
                if verify:
                    ok = mod.verify_record(node, rec, rho2)
                    nver += ok
                    rec['verified'] = ok
            recs.append({k: v for k, v in rec.items() if k != 'pack'} if backend == 'cvp' and not rec.get('certified') else rec)
            if with_min and D <= minmaxD:
                m = mod.min_node(node, D)
                mincomplete &= m['complete']
                minnn = m['nn'] if minnn is None else min(minnn, m['nn'])
            if backend == 'dual':
                types = Counter(tuple(x) for x in node['remaining'])
                labeled += node.get('mult', 1) * class_count_labeled(types, E, D)
        closed = ncert == len(nodes)
        row.update(status='CLOSED-sandwich' if closed else 'open', certified_nodes=ncert, verified_nodes=nver,
                   t_certify=round(time.time() - t0, 3), min_nn=None if minnn is None else str(minnn), min_complete=mincomplete,
                   labeled=labeled if backend == 'dual' else None)
        row['records'] = recs
        rows.append(row)
        log(row)
        if closed:
            break
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--patterns', default=os.path.join(ROOT, 'inputs', 'patterns-u2.jsonl'))
    ap.add_argument('--backend', required=True, choices=list(BACKENDS))
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', default=None)
    ap.add_argument('--maxD', type=int, default=3)
    ap.add_argument('--min', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--maxk', type=int, default=99)
    ap.add_argument('--mink', type=int, default=0)
    ap.add_argument('--minmaxD', type=int, default=99)
    ap.add_argument('--utable', default=None)
    args = ap.parse_args()
    pats = load_patterns(args.patterns)
    if args.utable:
        U = load_utable(args.utable)
        for p in pats:
            p['U'] = U[(p['k'], p['a'])]
    cache = {}
    with open(args.out, 'a') as fo:
        def log(row):
            fo.write(json.dumps(row, sort_keys=True) + '\n')
            fo.flush()
        for p in pats:
            if args.only and not p['id'].startswith(args.only):
                continue
            if p['k'] > args.maxk or p['k'] < args.mink:
                continue
            for ri, rep in enumerate(p['reps']):
                run_rep(p, ri, rep, args.backend, args.maxD, args.min, args.verify, log, cache, args.minmaxD)
                print(p['id'], 'rep', ri, 'done', flush=True)


if __name__ == '__main__':
    main()
