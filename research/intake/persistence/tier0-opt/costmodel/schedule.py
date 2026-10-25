#!/usr/bin/env python3
"""Plan only: LPT order of the remaining Tier A vertices. Executes nothing, writes nothing unless --json is given.
Reads the sweep's finished-vertex and finished-equation files, predicts per-vertex work with costmodel.py, and simulates
an equation/chunk-level pool over 4 P-cores + 6 E-cores (+ GPU lane for level 12) to give each vertex a predicted finish time.

  python3 schedule.py [--t12-ns 10] [--gpu 1e10] [--lvlN-x 1] [--post-x 1] [--open registered|fitted]
                      [--tier0 DIR] [--json out.json]
"""
import sys,os,json,argparse
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
ap=argparse.ArgumentParser()
ap.add_argument('--tier0',default='/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
ap.add_argument('--out-name',default='trees_mac.jsonl')
ap.add_argument('--t12-ns',type=float,default=10.0,help='CPU level-12 ns per pattern per P-core (ref 46, opt 10)')
ap.add_argument('--gpu',type=float,default=0.0,help='GPU level-12 patterns per second (0 = none)')
ap.add_argument('--lvlN-x',type=float,default=1.0,help='speedup of the lift engine vs the frozen reference')
ap.add_argument('--post-x',type=float,default=1.0,help='speedup of Lemma C and sandwich vs Python')
ap.add_argument('--open',default='registered',choices=['registered','fitted'])
ap.add_argument('--json'); a=ap.parse_args()
import scenarios as S
def rows(path):
    try:
        for l in open(path):
            try: yield json.loads(l)
            except Exception: pass
    except FileNotFoundError: return
done_v=set(); done_e=set()
for f in (a.out_name,'runall_final.jsonl','trees_c.jsonl'):
    for r in rows(os.path.join(a.tier0,f)): done_v.add(r.get('s'))
for r in rows(os.path.join(a.tier0,a.out_name+'.eqs.jsonl')): done_e.add((r['s'],tuple(r['M'])))
for v in S.V:
    v['vertex_done']=v['s'] in done_v
    for e in v['eqs']: e['done']=v['vertex_done'] or (v['s'],tuple(e['M'])) in done_e
sc=dict(t12=a.t12_ns*1e-9,lvlN_x=a.lvlN_x,post_x=a.post_x)
if a.gpu: sc['gpu']=a.gpu
R=S.eq_rows(a.open); tab=S.stage_table(R,sc)
fin,busy,tot,g=S.pool_sim(tab,sc)
per={}
for s,e,w,st in tab:
    d=per.setdefault(s,dict(s=s,eqs=0,patterns=0,work_Pcore_s=0.0,enum_s=0.0,lift_s=0.0,py_s=0.0,post_s=0.0))
    d['eqs']+=1; d['patterns']+=e['npat']; d['enum_s']+=st['lvl12']+st.get('gpu',0)
    d['lift_s']+=st['lvl24']+st['lvl48']+st['lvl96']; d['py_s']+=st['py']; d['post_s']+=st['lemmaC']+st['sandwich']
    d['work_Pcore_s']+=st['lvl12']+st['lvl24']+st['lvl48']+st['lvl96']+st['py']+st['lemmaC']+st['sandwich']
for s,d in per.items(): d['finish_h']=S.pool_sim.vfin.get(s,0)/3600
order=sorted(per.values(),key=lambda d:-d['work_Pcore_s'])
for i,d in enumerate(order,1): d['rank']=i
print(f"remaining Tier A vertices: {len(order)}  (done vertices skipped: {sum(v['vertex_done'] for v in S.V)}; finished equations skipped: {sum(e['done'] for v in S.V for e in v['eqs'])})")
print(f"scenario: t12={a.t12_ns} ns, gpu={a.gpu:g}/s, lvlN x{a.lvlN_x:g}, Lemma C/sandwich x{a.post_x:g}, open={a.open}")
print(f"pool makespan {fin/3600:.4g} h; capacity bound {tot/S.CAP/3600:.4g} h (cap {S.CAP:.1f} P-core equivalents)" + (f"; GPU lane {g/3600:.4g} h" if g else ''))
print("rank  vertex s            eqs   patterns    work(P-core h)  enum%  lift%  py%  post%  finish(h)")
for d in order:
    w=d['work_Pcore_s'] or 1
    print(f"{d['rank']:>4}  {d['s']:<18} {d['eqs']:>4}  {d['patterns']:.2e}  {d['work_Pcore_s']/3600:>13.4g}  {100*d['enum_s']/w:>5.1f} {100*d['lift_s']/w:>6.1f} {100*d['py_s']/w:>5.1f} {100*d['post_s']/w:>5.1f}  {d['finish_h']:>9.4g}")
if a.json: json.dump(dict(args=vars(a),makespan_h=fin/3600,order=order),open(a.json,'w'),indent=1)
