import sys, os, subprocess, hashlib
def run(src, M, out):
    code = f"import sys; sys.path.insert(0,'{src}'); from export_level import export; import json; info=[export({M!r}, L, '{out}_'+str(L)) for L in (24,48,96)]; print(json.dumps(info))"
    p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=src)
    assert p.returncode == 0, p.stderr[-500:]
    return p.stdout, [hashlib.sha256(open(f'{out}_{L}','rb').read()).hexdigest() for L in (24,48,96)]
src_a, src_b = sys.argv[1], sys.argv[2]
for M in [(2,2,2,2,2,2,2,2,2,2,2,7),(4,7,8,8,8),(2,3,7),(9,9,7,7,7,5)]:
    a = run(src_a, M, f'/private/tmp/persist-pydesc/cmpA'); b = run(src_b, M, f'/private/tmp/persist-pydesc/cmpB')
    print(M, 'info', a[0] == b[0], 'files', a[1] == b[1])
