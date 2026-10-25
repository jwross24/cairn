#!/usr/bin/env python3
"""Differential gate: C pipeline (lvl12 + lvlN) vs pure-Python engine, per equation, per level:
survivor counts, open counts, solutions. Usage: python3 difftest.py <vertex> <known,...>"""
import sys, json, os, subprocess
def runv(s, kn, env):
    p=subprocess.run(['python3','run_vertex_c.py',s,kn,'1'],capture_output=True,text=True,env={**os.environ,**env})
    rows=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
    if not rows: print("FAILED",s,env,p.stderr[-300:]); return None
    return rows
def key(e): return (tuple(e['M']), e['open'], tuple(e['sols']), tuple((l[0],l[1],l[3].get('OPEN',0)) for l in e['levels']))
if __name__=="__main__":
    s,kn=sys.argv[1],sys.argv[2]
    # apples to apples: eager descent on both paths (per-level OPEN counts are only comparable then)
    C=runv(s,kn,{'DESCENT_MAX':'1e18'}); P=runv(s,kn,{'NOCLIFT':'1','DESCENT_MAX':'1e18'})
    if C is None or P is None: sys.exit(1)
    kc={key(e) for e in C if 'M' in e}; kp={key(e) for e in P if 'M' in e}
    if kc==kp: print(f"vertex {s}: IDENTICAL ({len(kc)} equations)")
    else:
        print(f"vertex {s}: DIFFERENT"); 
        for k in sorted(kc^kp): print("  ", "C " if k in kc else "Py", k)
        sys.exit(2)
