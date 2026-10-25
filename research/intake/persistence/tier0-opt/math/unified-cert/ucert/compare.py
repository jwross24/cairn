import sys, os, json, argparse, re
from collections import defaultdict
from .env import *
from .run import load_oracle


def load_log(path):
    rows = {}
    for l in open(path):
        r = json.loads(l)
        rows[(r['pattern'], r['rep'], r['D'])] = r
    return rows


def parse_summary(path):
    out = []
    rx = re.compile(r'^s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\d+)\s+k=(\d+) reps=(\d+) log10G=(\S+) depth=(\d+) subcosets=(\d+) min-bound=(\S+) margin=(\S+)')
    for l in open(path):
        m = rx.match(l)
        if m:
            out.append(m.groups())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dual')
    ap.add_argument('--cvp')
    ap.add_argument('--patterns', default=os.path.join(ROOT, 'inputs', 'patterns-u2.jsonl'))
    ap.add_argument('--oracle', default=os.path.join(ROOT, 'oracle-u2', 'cport-sandwich-u2.tsv'))
    ap.add_argument('--summary', default=os.path.join(ROOT, 'oracle-u2', 'SANDWICH-full-U2.txt'))
    ap.add_argument('--out')
    ap.add_argument('--maxk', type=int, default=99)
    args = ap.parse_args()
    pats = [json.loads(l) for l in open(args.patterns)]
    orc = load_oracle(args.oracle)
    summ = parse_summary(args.summary)
    logs = {}
    if args.dual:
        logs['dual'] = load_log(args.dual)
    if args.cvp:
        logs['cvp'] = load_log(args.cvp)
    report = {'rep_rows': 0}
    for be in logs:
        report[be] = defaultdict(int)
    mism = []
    for pi, p in enumerate(pats):
        fk = p['id']
        if p['k'] > args.maxk:
            continue
        sm = summ[pi]
        for be, lg in logs.items():
            worstD, worst_sub, minb = 0, 0, None
            minb_missing = False
            allclosed = True
            for ri in range(len(p['reps'])):
                orows = orc[fk][ri]
                Ds = sorted(orows)
                for D in Ds:
                    res, stats, nn = orows[D]
                    r = lg.get((fk, ri, D))
                    report[be]['rows'] += 1
                    if r is None:
                        report[be]['missing'] += 1
                        mism.append((be, fk, ri, D, 'missing'))
                        continue
                    ok_status = r['status'] == res
                    report[be]['status_eq'] += ok_status
                    if not ok_status:
                        mism.append((be, fk, ri, D, 'status', res, r['status']))
                    if nn is not None and r.get('min_nn') is not None:
                        report[be]['min_rows'] += 1
                        eq = int(r['min_nn']) == nn and r.get('min_complete', True)
                        report[be]['min_eq'] += eq
                        if not eq:
                            mism.append((be, fk, ri, D, 'min_nn', str(nn)[:30], str(r['min_nn'])[:30]))
                    if be == 'dual' and r.get('labeled') is not None and stats not in ('-',):
                        report[be]['lab_rows'] += 1
                        eq = r['labeled'] == json.loads(stats)[-1]
                        report[be]['lab_eq'] += eq
                        if not eq:
                            mism.append((be, fk, ri, D, 'labeled', stats, r['labeled']))
                    if ok_status and r.get('verified_nodes') is not None:
                        report[be]['cert_nodes'] += r['certified_nodes']
                        report[be]['verified_nodes'] += r['verified_nodes']
                lrows = [lg[(fk, ri, D)] for D in sorted(d for (f2, r2, d) in lg if f2 == fk and r2 == ri)]
                closed = [r for r in lrows if r['status'] != 'open']
                if not closed:
                    allclosed = False
                    continue
                lr = closed[0]
                sub = 0 if lr['status'] == 'CLOSED-cut' else (lr.get('labeled') if be == 'dual' else json.loads(orows[lr['D']][1])[-1])
                b = None if lr.get('min_nn') is None else digits_bound_log10(int(lr['min_nn']))
                if lr['D'] > worstD or (lr['D'] == worstD and sub > worst_sub):
                    worstD, worst_sub = lr['D'], sub
                if b is None and lr['status'] != 'CLOSED-cut':
                    minb_missing = True
                if b is not None and (minb is None or b < minb):
                    minb = b
            ok = (str(worstD) == sm[7] and str(worst_sub) == sm[8] and (minb_missing or minb is None or f'{minb:.2f}' == sm[9]))
            report[be]['pattern_summary_eq'] += ok
            if not ok:
                mism.append((be, fk, 'summary', worstD, worst_sub, minb, sm[7:10]))
    if 'dual' in logs and 'cvp' in logs:
        c = defaultdict(int)
        for k, r in logs['dual'].items():
            r2 = logs['cvp'].get(k)
            if r2 is None:
                continue
            c['rows'] += 1
            c['status_eq'] += r['status'] == r2['status']
            if r.get('min_nn') is not None and r2.get('min_nn') is not None:
                c['min_rows'] += 1
                c['min_eq'] += r['min_nn'] == r2['min_nn']
            c['node_digest_eq'] += r['node_digests'] == r2['node_digests']
            if r['nodes'] != r2['nodes']:
                c['node_count_diff'] += 1
        report['dual_vs_cvp'] = dict(c)
    report = {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in report.items()}
    print(json.dumps(report, indent=1))
    print('mismatches', len(mism))
    for m in mism[:40]:
        print(m)
    if args.out:
        json.dump({'report': report, 'mismatches': [list(map(str, m)) for m in mism]}, open(args.out, 'w'), indent=1)
