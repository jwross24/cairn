import sys, json
a, b = sys.argv[1], sys.argv[2]
def rows(f):
    out = []
    for ln in open(f):
        if not ln.startswith('{'): continue
        d = json.loads(ln); d.pop('secs', None)
        if 'vertex' in d: continue
        d.pop('open_patterns', None)
        for e in d.get('eqs', []): e.pop('open_patterns', None)
        out.append(json.dumps(d))
    return out
ra, rb = rows(a), rows(b)
print(f"rows {len(ra)} vs {len(rb)} equal={ra == rb}")
sys.exit(0 if ra == rb and ra else 1)
