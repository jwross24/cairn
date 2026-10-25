import sys, json, os
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for fn in sorted(os.listdir(src)):
    if not fn.endswith('.jsonl'): continue
    with open(os.path.join(src, fn)) as f, open(os.path.join(dst, fn), 'w') as g:
        for line in f:
            r = json.loads(line); r.pop('secs', None)
            g.write(json.dumps(r, sort_keys=True) + '\n')
