import sys, os, subprocess, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = '/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad'
H = os.path.join(SCR, 'h12')
os.makedirs(os.path.join(SCR, 'dj'), exist_ok=True)

def gate():
    return subprocess.run([sys.executable, os.path.join(HERE, 'gate.py')]).returncode == 0

def dirs_with(level, minchildren):
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, 'logs', 'h12_*.jsonl'))):
        for l in open(f):
            r = json.loads(l)
            x = r.get(f'lift{level}')
            if x and x['children'] >= minchildren:
                out.append((x['children'] / max(x['parents'], 1), os.path.join(H, f"{r['s']}_{''.join(map(str, r['M']))}")))
    out.sort()
    return [d for _, d in out]

def run(level, dirs, outname, env_extra=None):
    env = dict(os.environ); env.update(env_extra or {}); env['PYTHONDONTWRITEBYTECODE'] = '1'
    with open(os.path.join(HERE, 'logs', outname), 'w') as fo:
        subprocess.run([sys.executable, os.path.join(HERE, 'diff_join.py'), os.path.join(SCR, 'dj'), str(level)] + dirs, stdout=fo, env=env)

if __name__ == '__main__':
    if not gate(): print('compute gate closed'); sys.exit(2)
    d24 = dirs_with(24, 3e6); d48 = dirs_with(48, 1e6)
    run(24, d24, 'join24_diff.jsonl')
    if gate(): run(48, d48, 'join48_diff.jsonl')
    top24 = d24[-3:]; top48 = d48[-3:]
    for m in (1, 2):
        if gate():
            run(24, top24, f'join24_mut{m}.jsonl', {'JOIN_MUTANT': str(m)})
            run(48, top48, f'join48_mut{m}.jsonl', {'JOIN_MUTANT': str(m)})
    for fs, name in ((0, 'set0'), (2, 'set2'), (3, 'set3'), (4, 'set4')):
        if gate(): run(24, d24[-6:], f'join24_force{fs}.jsonl', {'JOIN_FORCE_SET': str(fs)})
