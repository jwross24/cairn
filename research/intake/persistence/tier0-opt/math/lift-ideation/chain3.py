import subprocess, os, json, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def go(level, log, n, variants, env=None):
    e = dict(os.environ); e.update(env or {})
    subprocess.run(['uv', 'run', '--no-project', 'python', os.path.join(HERE, 'ldiff.py'), str(level), log, str(n), json.dumps(variants)], env=e, cwd=HERE)
M5 = {"name": "fpM5", "bin": "lvlJ3m5", "env": {"JOIN_FP": "1", "JOIN_MUTANT": "5"}, "min_count": 1}
go(24, 'fp_m5_24.jsonl', 30, [M5], {'LDIFF_TIMEOUT': '900', 'LDIFF_CH': '2e5:3e8', 'LDIFF_DESC': '1'})
go(48, 'fp_m5_48.jsonl', 40, [M5], {'LDIFF_TIMEOUT': '900', 'LDIFF_CH': '1e5:1e10', 'LDIFF_DESC': '1'})
