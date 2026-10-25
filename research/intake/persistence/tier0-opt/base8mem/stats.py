import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
sys.argv = ["x", "8", "70", "12,24,48,96", "/dev/null", "1"]
import run_base_mp as R
rows = {}
for l in open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0/base8_L96.jsonl"):
    r = json.loads(l); rows[r['s']] = r
out = []
for t, s in R.verts:
    ms = R.base.multisets(s)
    out.append((R.npat(s), s, t, len(ms), rows[s]['secs'] if s in rows else None, rows[s]['open'] if s in rows else None))
out.sort(reverse=True)
for o in out[:14]: print(o)
