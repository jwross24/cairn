import subprocess, os, json, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def go(level, log, n, variants, env=None):
    e = dict(os.environ); e.update(env or {})
    subprocess.run(['uv', 'run', '--no-project', 'python', os.path.join(HERE, 'ldiff.py'), str(level), log, str(n), json.dumps(variants)], env=e, cwd=HERE)
FP = {"name": "fp", "env": {"JOIN_FP": "1"}}
FPM = {"name": "fpM4", "env": {"JOIN_FP": "1", "JOIN_MUTANT": "4"}, "min_count": 1}
W3 = {"name": "way3", "env": {"JOIN_WAY": "3"}}
J = {"name": "join"}
go(24, 'fp_way3_24.jsonl', 60, [J, W3, FP, FPM], {'LDIFF_TIMEOUT': '900', 'LDIFF_CH': '2e5:3e8', 'LDIFF_DESC': '1'})
go(48, 'fp_way3_48.jsonl', 60, [J, W3, FP, FPM], {'LDIFF_TIMEOUT': '900', 'LDIFF_CH': '1e5:1e10', 'LDIFF_DESC': '1'})
