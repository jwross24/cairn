import sys, json, os
ref = {}
for l in open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0/base8_L96.jsonl"):
    r = json.loads(l); ref[r['s']] = r
def norm(r):
    r = dict(r); r.pop('secs'); return json.loads(json.dumps(r))
d = sys.argv[1]
bad = 0; n = 0
for f in sorted(os.listdir(d)):
    if not f.endswith(".json"): continue
    s = int(f[:-5]); got = json.load(open(os.path.join(d, f))); n += 1
    same = norm(got) == norm(ref[s])
    print(s, "EQUAL" if same else "DIFFERS")
    bad += not same
print("compared", n, "mismatches", bad)
sys.exit(1 if bad or n == 0 else 0)
