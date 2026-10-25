import sys, os, json, subprocess
pipe, s = sys.argv[1], int(sys.argv[2])
from math import prod
known = []
LIM = 10 ** 200
a2 = 1
while a2 < LIM:
    b3 = a2
    while b3 < LIM:
        y = b3
        while y < LIM:
            t = str(y)
            if y >= 10 and '0' not in t and prod(int(ch) for ch in t if ch != '1') == s:
                known.append(y)
            y *= 7
        b3 *= 3
    a2 *= 2
known.sort()
p = subprocess.run([sys.executable, 'run_vertex_c.py', str(s), ','.join(map(str, known)), '1'], cwd=pipe, capture_output=True, text=True)
rows = []
for ln in p.stdout.splitlines():
    if ln.startswith('{'):
        d = json.loads(ln)
        d.pop('secs', None)
        rows.append(d)
print('VERTEX ' + json.dumps(dict(rc=p.returncode, known=known, rows=rows, err=p.stderr[-400:] if p.returncode else '')))
