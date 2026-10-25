import sys, hashlib

ref_path, new_path = sys.argv[1], sys.argv[2]
v43 = sys.argv[3] if len(sys.argv) > 3 else None


def rows(p):
    with open(p) as f:
        return [l.rstrip('\n') for l in f]


ref, new = rows(ref_path), rows(new_path)
vcols = (5, 6, 7, 8, 9, 10)
bad = []
if len(ref) != len(new):
    bad.append(('row count', len(ref), len(new)))
for i, (r, n) in enumerate(zip(ref, new)):
    rp, np_ = r.split('\t'), n.split('\t')
    if rp[0] != np_[0]:
        bad.append(('key', i, rp[0], np_[0]))
        continue
    for c in vcols:
        if rp[c] != np_[c]:
            bad.append(('col', i, c, rp[c], np_[c]))
print('rows', len(ref), len(new), 'verdict-column differences', len(bad))
print('sha256 ref', hashlib.sha256('\n'.join(ref).encode()).hexdigest()[:16], 'new', hashlib.sha256('\n'.join(new).encode()).hexdigest()[:16], 'whole-file byte equal', ref == new)
for b in bad[:10]:
    print(b)
if v43:
    vm = {}
    with open(v43) as f:
        next(f)
        for l in f:
            p = l.rstrip('\n').split('\t')
            vm[(p[0], p[1], p[2], p[3])] = p[7]
    nb = 0
    for n in new:
        p = n.split('\t')
        key = (p[1], p[2], p[3], p[4])
        want = vm[key]
        got = "('%s', %s)" % (p[7], repr(p[8]) if p[8] else 'None')
        if want != got:
            nb += 1
            print('VERDICTS_43 mismatch', key, want, got)
    print('VERDICTS_43 C-full column mismatches', nb, 'of', len(new))
sys.exit(1 if bad else 0)
