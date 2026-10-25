import sys, os, subprocess, hashlib
def run(src, M, out):
    code = f"import sys; sys.path.insert(0,'{src}'); from export_cfg import export; import json; c=export({M!r}, '{out}'); print(json.dumps(c, sort_keys=False))"
    p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=src)
    assert p.returncode == 0, p.stderr[-500:]
    h = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
    return hashlib.sha256(p.stdout.encode()).hexdigest(), h(out), h(out + '.json')
a_, b_ = sys.argv[1], sys.argv[2]
for M in [(2,)*12+(7,), (4,7,8,8,8), (2,3,7), (9,9,7,7,7,5), (6,), (8,8,8,8,8,8,8,8,8,8,8,8)]:
    a = run(a_, M, '/private/tmp/persist-pydesc/cmpA12'); b = run(b_, M, '/private/tmp/persist-pydesc/cmpB12')
    print(M, 'returned cfg', a[0] == b[0], 'txt', a[1] == b[1], 'json', a[2] == b[2])
