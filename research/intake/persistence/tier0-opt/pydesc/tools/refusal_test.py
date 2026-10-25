"""refusal_test.py : run_c.run against fake lvl12 / lvlN outputs; old and new modules must raise the same errors or return the same result"""
import sys, os, subprocess, json, textwrap
CASES = {
 'blank_line': "OPEN 0 5 3 3 0 0\n\nOPEN 0 6 3 3 1 1\n",
 'short_open': "OPEN 0 5 3\n",
 'nonint': "OPEN 0 5 3 3 x 0\n",
 'unknown_kind': "DEAD 1 2 3\nOPEN 0 5 3 3 0 0\n",
 'exact_short': "EXACT 0 5 3 3 0\n",
 'exact_ok': "EXACT 0 5 3 3 0 0 99\nOPEN 0 5 3 3 0 0\n",
 'plus_sign': "OPEN 0 +5 3 3 0 0\n",
 'underscore': "OPEN 0 5 3 3 1_0 0\n",
 'neg': "OPEN 0 5 3 3 -4 7\nOPEN 1 6 2 3 5 -9\n",
 'extra_tokens': "OPEN 0 5 3 3 0 0 extra tokens here\n",
 'huge': "OPEN 0 5 3 3 123456789012345678901234567890 -98765432109876543210\n",
 'empty': "",
 'ws_only': "   \n",
 'crlf': "OPEN 0 5 3 3 0 0\r\nOPEN 0 6 3 3 1 1\r\n",
 'nonzero_rc': "OPEN 0 5 3 3 0 0\n#RC1\n",
 'many': ''.join(f"OPEN {i%3} {i%12} {(i*7)%12} {(i*5)%12} {i} {-i}\n" for i in range(300)),
}
child = r'''
import sys, os, json, traceback
src, case_file = sys.argv[1], sys.argv[2]
os.chdir(src); sys.path.insert(0, src)
import run_c
try:
    r = run_c.run(6, (2, 3), [], ncores=1)
    out = dict(ok=True, open=len(r['open']), sols=sorted(r['solutions']), levels=[(l[0], l[2], l[3], l[4]) for l in r['levels']], c_stats=r['c_stats'])
except BaseException as e:
    out = dict(ok=False, exc=type(e).__name__, msg=str(e)[:200])
print('RESULT ' + json.dumps(out, default=str))
'''
def setup(srcdir, workroot, case, text):
    d = os.path.join(workroot, os.path.basename(srcdir) + '_' + case); os.makedirs(d, exist_ok=True)
    for f in os.listdir(srcdir):
        p = os.path.join(srcdir, f)
        if os.path.isfile(p) and f not in ('lvl12',):
            dst = os.path.join(d, f)
            if not os.path.lexists(dst): os.symlink(p, dst)
    fake = os.path.join(d, 'lvl12')
    if os.path.lexists(fake): os.remove(fake)
    body = text.replace('#RC1\n', '')
    rc = 1 if '#RC1' in text else 0
    open(os.path.join(d, 'fake.out'), 'w').write(body)
    open(fake, 'w').write(f"#!/bin/sh\ncat \"$(dirname \"$0\")/fake.out\"\nexit {rc}\n"); os.chmod(fake, 0o755)
    return d
a, b = sys.argv[1], sys.argv[2]
work = '/private/tmp/persist-pydesc/refusal'
os.makedirs(work, exist_ok=True)
bad = 0
for case, text in CASES.items():
    res = []
    for src in (a, b):
        d = setup(src, work, case, text)
        p = subprocess.run([sys.executable, '-c', child, d, 'x'], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED='0'))
        line = [l for l in p.stdout.splitlines() if l.startswith('RESULT ')]
        res.append(line[0] if line else 'NO RESULT: ' + p.stderr[-300:])
    same = res[0] == res[1]
    bad += not same
    print(f"{case:14s} {'SAME' if same else 'DIFFERENT'}  {res[0][:150]}")
    if not same: print('   new:', res[1][:300])
sys.exit(1 if bad else 0)
