import json, sys
sys.dont_write_bytecode = True
rows = []
for f in ("proto_out.jsonl", "proto2_out.jsonl", "proto_neg2.jsonl"):
    try:
        for l in open(f):
            if l.startswith("{"):
                r = json.loads(l)
                rows.append((f, r))
    except FileNotFoundError:
        pass
print("| file | s | P=K | nmax | multisets | pairs | queries | a-free pairs | tails with empty coset | lattice points enumerated | found | found by a pair query | recorded | agree |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for f, r in rows:
    print(f"| {f} | {r['s']} | {r['P']} | {r['nmax']} | {r['multisets']} | {r['pairs']} | {r['queries']} | {r['a_free_pairs']} | {r['coset_empty']} | {r['enum_points']} | {r['found']} | {r.get('found_by_pair_query','-')} | {r['recorded_known']} | {r['agree']} |")
