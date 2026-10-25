import sys, os; sys.path.insert(0, os.getcwd())
import sys, os, json, hashlib, subprocess, tempfile, time
from collections import Counter
from math import comb
from export_cfg import export
from tier0v2 import multisets
# usage: vertex_hash.py <lvl12 binary> <vertex> <out.json> <ncores>
binp, s, out, nc = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
def npat(M):
    p = 12
    for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
    return p
eqs = sorted(tuple(sorted(M)) for M in multisets(s))
res = {}; allh = hashlib.sha256(); tot_lines = 0; tot_pat = 0
tmp = tempfile.mkdtemp(prefix='vh_')
t0 = time.time()
for M in eqs:
    cfgp = f"{tmp}/c_{''.join(map(str, M))}.txt"; export(M, cfgp)
    procs = []
    for i in range(nc):
        lo, hi = 12 * i // nc, 12 * (i + 1) // nc
        of = open(f"{cfgp}.{i}.out", 'w')
        procs.append((subprocess.Popen(['nice', '-n', '10', binp, cfgp, str(lo), str(hi)], stdout=of, stderr=subprocess.PIPE, text=True), of))
    lines = []; cnt = Counter()
    for p, of in procs:
        _, err = p.communicate(); of.close(); assert p.returncode == 0, err
        parts = err.split()
        for k, v in zip(parts[0::2], parts[1::2]): cnt[k] += int(v)
    for i in range(nc):
        with open(f"{cfgp}.{i}.out") as f: lines += f.read().splitlines()
        os.remove(f"{cfgp}.{i}.out")
    lines.sort()
    h = hashlib.sha256('\n'.join(lines).encode()).hexdigest()
    key = ''.join(map(str, M))
    res[key] = dict(nlines=len(lines), sha=h, counters=dict(cnt)); tot_lines += len(lines); tot_pat += cnt['patterns']
    allh.update(key.encode() + b'\n' + h.encode() + b'\n' + json.dumps(dict(cnt), sort_keys=True).encode() + b'\n')
    print(f"{key} lines={len(lines)} patterns={cnt['patterns']} sha={h[:12]} t={time.time()-t0:.1f}s", flush=True)
    os.remove(cfgp); os.remove(cfgp + '.json')
summary = dict(vertex=s, equations=len(eqs), lines=tot_lines, patterns=tot_pat, overall_sha=allh.hexdigest(), secs=round(time.time() - t0, 1), per_equation=res)
json.dump(summary, open(out, 'w'), indent=1, sort_keys=True)
print("OVERALL", s, "equations", len(eqs), "lines", tot_lines, "patterns", tot_pat, "sha", summary['overall_sha'], flush=True)
