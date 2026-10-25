import sys, os, subprocess, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = '/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad'
H = os.path.join(SCR, 'h12')

def gate():
    return subprocess.run([sys.executable, os.path.join(HERE, 'gate.py')]).returncode == 0

def one(s, M, mutant=None, tag=''):
    name = f"{s}_{''.join(map(str, M))}"
    cfg = os.path.join(H, name, f'cfg_{name}.txt')
    A = open(cfg).readline().split()[1]
    out = os.path.join(SCR, f'dual_{name}{tag}'); os.makedirs(out, exist_ok=True)
    env = dict(os.environ)
    if mutant: env['DUAL_MUTANT'] = str(mutant)
    import time; t = time.time()
    subprocess.run([os.path.join(HERE, 'run_dual.sh'), out, A] + [str(d) for d in M], env=env, check=True)
    wall = time.time() - t
    errs = [open(os.path.join(out, f'dual_{x}.err')).read().strip() for x in 'ab']
    r = subprocess.run([sys.executable, os.path.join(HERE, 'diff_dual.py'), os.path.join(H, 'dump', name + '.l12'), str(len(M)),
                        os.path.join(out, 'dual_a.out'), os.path.join(out, 'dual_b.out')], capture_output=True, text=True).stdout.strip()
    d = json.loads(r); d.update(s=s, M=list(M), A=int(A), mutant=mutant, wall=round(wall, 1), dual_stats=errs)
    print(json.dumps(d), flush=True)

if __name__ == '__main__':
    if not gate():
        print('compute gate closed'); sys.exit(2)
    suite = [(28672, (7, 8, 8, 8, 8)), (14336, (4, 7, 8, 8, 8)), (124416, (3, 8, 8, 8, 9, 9)), (124416, (4, 4, 6, 6, 6, 6, 6))]
    for s, M in suite:
        if not gate(): print('gate closed'); break
        one(s, M)
    for m in (3, 1, 2):
        if not gate(): break
        one(*suite[0], mutant=m, tag=f'_mut{m}')
