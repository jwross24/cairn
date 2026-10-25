import json, glob
rows={}
for l in open('/Users/jwross/Documents/cairn/research/intake/persistence/tier0/trees_mac.jsonl.eqs.jsonl'):
    d=json.loads(l); rows[(d['s'],tuple(d['M']))]=d
tot=dict(n=0,fail=0,fid=0)
for p in sorted(glob.glob('results/*.json')):
    r=json.load(open(p))
    if r['A']<64: continue
    rec=rows[(r['s'],tuple(r['M']))]
    recl=[tuple(x[:3]) for x in rec['levels']]; prl=[tuple(x) for x in r['prod']['levels']]
    fid=(recl==prl) and rec['open']==r['prod']['open']
    pl=r['prod']['per_level']
    s=' '.join(f"L{x['level']}:F\\P={x['fixed_not_in_prod']} P\\F={x['prod_not_in_fixed']} (P={x['prod_keys']},F={x['fixed_keys']})" for x in pl)
    fail=any(x['fixed_not_in_prod']>0 for x in pl)
    tot['n']+=1; tot['fail']+=fail; tot['fid']+=fid
    print(f"{r['s']} k={len(r['M'])} A={r['A']} recorded_reproduced={fid} recorded_open={rec['open']} prod_open={r['prod']['open']} fixed_open={r['fixed']['open']} | {s} | SOUNDNESS_FAIL={fail}")
print(tot)
