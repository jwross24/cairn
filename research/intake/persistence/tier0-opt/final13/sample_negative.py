import json, os, random, subprocess, sys, time

F = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13'
CP = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport'
st = json.load(open(F + '/d1/pattern_status.json'))
order = sorted((fk for fk, v in st.items() if v == 'unrun'), key=lambda fk: (len(fk.split()[1]), fk))
done = [(n, fk) for n, fk in enumerate(order) if os.path.exists(f'{F}/full/sw/{n}.cases') and any(l.startswith('s=') for l in open(f'{F}/full/sw/{n}.txt'))]
small = [(n, fk) for n, fk in done if len(fk.split()[1]) <= 12]
rnd = random.Random(13)
sample = rnd.sample(small, 200)
inflated = F + '/neg/utable_inflated_400.txt'
os.makedirs(F + '/neg', exist_ok=True)
with open(inflated, 'x') as f:
    for l in open(F + '/full/utable.txt'):
        t = l.split()
        f.write(f'{t[0]} {t[1]} {10 ** 400}\n')
out = open(F + '/neg/sample_negative.tsv', 'x')
closed = refused = other = 0
t0 = time.time()
for n, fk in sample:
    base = f'{F}/neg/p{n}'
    open(base + '.cases', 'x').write(fk + '\n')
    open(base + '.only', 'x').write(' '.join(fk.split()[:4]) + '\n')
    cmd = [CP + '/cport', 'sandwich', '--dfs', '--lattice', CP + '/data/lattice96.txt', '--utable', inflated, '--cases', base + '.cases', '--only', base + '.only',
           '--maxdepth', '5', '--maxcases', '2000000', '--tsv', base + '.tsv']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, preexec_fn=lambda: os.nice(10))
        line = next((l for l in r.stdout.splitlines() if l.startswith('s=')), '')
        res = 'CLOSED' if ' -> CLOSED' in line else ('REFUSED' if line else 'NOLINE')
        if r.returncode:
            res = 'ERROR'
    except subprocess.TimeoutExpired:
        res = 'TIMEOUT'
    out.write(f'{n}\t{fk}\t{res}\n')
    out.flush()
    closed += res == 'CLOSED'
    refused += res == 'REFUSED'
    other += res not in ('CLOSED', 'REFUSED')
print('sample', len(sample), 'closed under inflated table', closed, 'refused', refused, 'other', other, 'wall', round(time.time() - t0))
