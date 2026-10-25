import sys, os, subprocess, resource, hashlib, json
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0'))

def run(binary, cfg, par, outp, env=None):
    e = dict(os.environ); e.update(env or {})
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with open(outp, 'w') as fo:
        pr = subprocess.run(['nice', '-n', '10', binary, cfg, par], stdout=fo, stderr=subprocess.PIPE, text=True, env=e)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    stats = {}
    parts = pr.stderr.split()
    for k, v in zip(parts[0::2], parts[1::2]):
        try: stats[k] = int(v)
        except ValueError: pass
    return pr.returncode, cpu, stats

def canon(path):
    lines = sorted(l for l in open(path) if l.strip())
    h = hashlib.sha256(''.join(lines).encode()).hexdigest()
    return len(lines), h

if __name__ == '__main__':
    scratch = sys.argv[1]; level = sys.argv[2]; dirs = sys.argv[3:]
    mut = os.environ.get('JOIN_MUTANT', '')
    for d in dirs:
        cfg = os.path.join(d, f'cfgL{level}.txt'); par = os.path.join(d, f'parents{level}.txt')
        if not os.path.exists(par): print(d, 'no parents'); continue
        rc1, c1, s1 = run(os.path.join(T0, 'lvlN'), cfg, par, os.path.join(scratch, 'ref.out'))
        rc2, c2, s2 = run(os.path.join(HERE, 'lvlJ'), cfg, par, os.path.join(scratch, 'join.out'))
        n1, h1 = canon(os.path.join(scratch, 'ref.out')); n2, h2 = canon(os.path.join(scratch, 'join.out'))
        keys = ('parents', 'children', 'tail-dead', 'open', 'exact')
        same_stats = all(s1.get(k) == s2.get(k) for k in keys)
        print(json.dumps(dict(dir=os.path.basename(d), level=level, mutant=mut, rc=[rc1, rc2], lines=[n1, n2], identical=(n1 == n2 and h1 == h2), stats_equal=same_stats,
                              parents=s1.get('parents'), children=s1.get('children'), cpu_ref=round(c1, 3), cpu_join=round(c2, 3),
                              speedup=round(c1 / c2, 2) if c2 > 0 else None, probes=s2.get('probes'), cands=s2.get('cands'), built=s2.get('built'), K=s2.get('K'))), flush=True)
