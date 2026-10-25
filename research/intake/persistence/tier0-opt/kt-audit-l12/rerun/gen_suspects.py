import sys, json, os
sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
os.chdir(T0)
from tier0v2 import two_adic_bound

SWAP = 1792646338
OUT = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/kt-audit-l12/rerun/suspects.tsv'

def rows(f):
    return [json.loads(l) for l in open(f)]

mac = rows('trees_mac.jsonl')
eqf = rows('trees_mac.jsonl.eqs.jsonl')
tc = rows('trees_c.jsonl')
inmac = {}
out = []
for ri, r in enumerate(mac):
    for e in r['eqs']:
        inmac[(r['s'], tuple(e['M']))] = 1
        A = two_adic_bound(tuple(e['M']))
        if A >= 64:
            out.append((r['s'], ''.join(map(str, e['M'])), A, 'A>=68' if A >= 68 else 'A64-67', 'trees_mac.jsonl', f'row{ri}', 'pre-swap(row mtime 1792640071 < swap)', e['open'], e['npat']))
n_tc = sum(1 for r in tc for e in r['eqs'] if two_adic_bound(tuple(e['M'])) >= 64)
for li, d in enumerate(eqf):
    k = (d['s'], tuple(d['M']))
    if k in inmac:
        continue
    A = two_adic_bound(tuple(d['M']))
    if A >= 64:
        out.append((d['s'], ''.join(map(str, d['M'])), A, 'A>=68' if A >= 68 else 'A64-67', 'trees_mac.jsonl.eqs.jsonl', f'line{li}', 'in-progress vertex; finished before last eqs write (inferred pre-swap)', d['open'], d['npat']))
out.sort(key=lambda t: t[8])
with open(OUT, 'w') as f:
    f.write('\t'.join(['s', 'M', 'A', 'class', 'file', 'row', 'timing', 'recorded_open', 'npat']) + '\n')
    for t in out:
        f.write('\t'.join(map(str, t)) + '\n')
print(len(out), 'suspects;', sum(1 for t in out if t[3] == 'A>=68'), 'A>=68;', 'trees_c A>=64 eqs:', n_tc)
