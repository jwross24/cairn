import json, sys, os
import bsgate
LOGS = '../logs'
REC = '../../../../tier0/trees_mac.jsonl.eqs.jsonl'
for s in (8192, 14336, 28672):
    with open(f'{LOGS}/prod_recorded_{s}.jsonl', 'w') as fo:
        for l in open(REC):
            if json.loads(l)['s'] == s:
                fo.write(l)
pairs = [('v72_off', 'v72_on'), ('v224_off', 'v224_on'), ('v10800_off', 'v10800_on'), ('v14336_off', 'v14336_on'),
         ('prod_recorded_14336', 'v14336_on'), ('prod_recorded_8192', 'v8192_on'), ('prod_recorded_28672', 'v28672_on')]
if len(sys.argv) > 1:
    pairs = [tuple(a.split(':')) for a in sys.argv[1:]]
for b, n in pairs:
    rep = bsgate.compare(bsgate.load(f'{LOGS}/{b}.jsonl'), bsgate.load(f'{LOGS}/{n}.jsonl'))
    out = {k: (dict(v) if hasattr(v, 'items') else v) for k, v in rep.items()}
    with open(f'{LOGS}/gate_{n}_vs_{b}.json', 'w') as fo:
        json.dump(out, fo, default=str)
    lp, ln = out['levels_prod'], out['levels_new']
    print(f"== {n} vs {b}: eq={out['equations']} sols_identical={out['sols_identical']} sols_diff={len(out['sols_diff'])} refused={len(out['refused'])} "
          f"open_subset={out['open_subset']} not_subset={len(out['open_not_subset'])} coset_diff={len(out['coset_diff'])}")
    print("   removed", out['removed'], dict(out['removed_checks']), dict(out['removed_anchor']))
    for L in (12, 24, 48, 96):
        print(f"   L={L}: survivors prod {lp.get(L,lp.get(str(L),0))} new {ln.get(L,ln.get(str(L),0))}  tested prod {out['nin_prod'].get(L,out['nin_prod'].get(str(L),0))} new {out['nin_new'].get(L,out['nin_new'].get(str(L),0))}")
