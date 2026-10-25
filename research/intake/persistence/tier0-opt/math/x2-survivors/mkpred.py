import json, collections, math, subprocess, hashlib
from scipy.stats import poisson, chi2

rows = [json.loads(l) for l in open('model_out.jsonl')]
def pint(mu, lvl=0.95):
    a = (1 - lvl) / 2
    lo = int(poisson.ppf(a, mu)) if mu > 0 else 0
    hi = int(poisson.ppf(1 - a, mu)) if mu > 0 else 0
    return lo, hi
flag = {r['eq'] for r in rows if r['A'] >= 64}
with open('model_table.csv', 'w') as f:
    f.write('eq,k,A,A_ge_64,children,E_resid,E_resid_lo95,E_resid_hi95,E_tail,E_tail_se,E_tail_lo95,E_tail_hi95\n')
    for r in rows:
        lo, hi = pint(r['E_resid']); tlo, thi = pint(r['E_tail'])
        f.write(f"{r['eq']},{r['q']},{r['A']},{int(r['A']>=64)},{r['children']},{r['E_resid']:.4f},{lo},{hi},{r['E_tail']:.4f},{r['E_tail_se']:.4f},{tlo},{thi}\n")
def agg(sel):
    n = len(sel); ch = sum(r['children'] for r in sel); er = sum(r['E_resid'] for r in sel); et = sum(r['E_tail'] for r in sel)
    se = math.sqrt(sum(r['E_tail_se'] ** 2 for r in sel))
    return n, ch, er, et, se
lines = []
lines.append('| k | equations | children | E_R residue accidents [95% Poisson] | E_T tail-passing accidents +- MC se [95% Poisson] |')
lines.append('|---|---|---|---|---|')
for k in sorted({r['q'] for r in rows}):
    n, ch, er, et, se = agg([r for r in rows if r['q'] == k and r['eq'] not in flag])
    if n == 0: continue
    lo, hi = pint(er); tlo, thi = pint(et)
    lines.append(f"| {k} | {n} | {ch} | {er:.1f} [{lo}, {hi}] | {et:.2f} +- {se:.2f} [{tlo}, {thi}] |")
for name, sel in (('all 225 excluding A>=64', [r for r in rows if r['eq'] not in flag]),
                  ('k<=12 excluding A>=64', [r for r in rows if r['q'] <= 12 and r['eq'] not in flag]),
                  ('k>=13 excluding A>=64', [r for r in rows if r['q'] >= 13 and r['eq'] not in flag]),
                  ('A>=64 (3 equations, reported separately)', [r for r in rows if r['eq'] in flag])):
    n, ch, er, et, se = agg(sel); lo, hi = pint(er); tlo, thi = pint(et)
    lines.append(f"| {name} | {n} | {ch} | {er:.1f} [{lo}, {hi}] | {et:.2f} +- {se:.2f} [{tlo}, {thi}] |")
open('model_pooled.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines)); print(sorted(flag))
