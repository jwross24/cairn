import subprocess, os, json, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def go(level, log, n, variants, env=None):
    e = dict(os.environ); e.update(env or {})
    subprocess.run(['uv', 'run', '--no-project', 'python', os.path.join(HERE, 'ldiff.py'), str(level), log, str(n), json.dumps(variants)], env=e, cwd=HERE)
G = {"name": "gpu", "bin": "lvlG"}; GM = {"name": "gpuM", "bin": "lvlG", "env": {"GPU_MUTANT": "1"}, "min_count": 8}
go(24, 'gpu24_top.jsonl', 40, [G, {"name": "join"}, GM], {'LDIFF_TIMEOUT': '900', 'LDIFF_CH': '1e7:3e8', 'LDIFF_DESC': '1'})
go(48, 'join48_clean.jsonl', 400, [{"name": "join"}, {"name": "M1", "env": {"JOIN_MUTANT": "1"}, "min_count": 1}, {"name": "M1p", "env": {"JOIN_MUTANT": "3"}, "min_count": 1}, {"name": "M2", "env": {"JOIN_MUTANT": "2"}, "min_count": 1}], {'LDIFF_TIMEOUT': '900'})
go(48, 'gpu48_clean.jsonl', 400, [G, GM], {'LDIFF_TIMEOUT': '900'})
