#!/usr/bin/env python3
"""tables_b.py — markdown tables for a base-b run.  python3 tables_b.py <b> <jsonl> > TABLE-base<b>.md"""
import sys, json
from collections import Counter
from engine_b import Base

b = int(sys.argv[1]); rows = [json.loads(l) for l in open(sys.argv[2])]
base = Base(b)
rows.sort(key=lambda r: (r['target'], r['s']))
summary = Counter('CLOSED' if r['status'] == 'CLOSED' else ('closed-below-height' if 'BELOW' in r['status'] else r['status']) for r in rows)
bounds = [float(r['status'].split('10^')[1].split()[0]) for r in rows if 'BELOW' in r['status']]
print(f"# Base {b}: antecedent trees of the nonzero digital roots\n")
print(f"{len(rows)} vertices (roots included). Status counts: {dict(summary)}."
      + (f" Height bounds (digits) for the closed-below vertices: min 10^{min(bounds):.1e}." if bounds else ""))
print(f"Levels used: {rows[0]['eqs'][0]['levels'][0][0] if rows[0]['eqs'] else '-'}…{max(L for r in rows for e in r['eqs'] for (L, *_ ) in e['levels'])}.\n")
print("| target | vertex s | s in base " + str(b) + " | factorization | equations | level-1 patterns | open patterns | status | children (base 10) | secs |")
print("|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    f = base.factor(r['s'])
    fct = '·'.join(f"{p}^{e}" if e > 1 else str(p) for p, e in zip(base.dp, f) if e) or '1'
    pats = sum(e['levels'][0][1] for e in r['eqs'] if e['levels'])
    st = r['status'].replace('CLOSED BELOW 10^', 'closed <10^').replace(' DIGITS', ' digits')
    print(f"| {r['target']} | {r['s']} | {'.'.join(map(str, base.digits(r['s'])))} | {fct} | {len(r['eqs'])} | {pats:.2e} | {r['open']} | {st} | {' '.join(map(str, r['found'])) or '—'} | {r['secs']} |")
# known vs found
bad = [r for r in rows if r['found'] != r['known']]
print(f"\nVertices where found ≠ corpus children: {len(bad)}" + (": " + str([(r['s'], r['found'], r['known']) for r in bad]) if bad else " (none)."))
# persistence
print("\nPersistence: the maximum over all corpus elements with nonzero digital root is attained on the listed trees; see PROGRAM-BASES.md.")
