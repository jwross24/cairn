import sys, json, glob, collections, re, os
S = '/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/final_u2/sw/'
old = {}
for f in glob.glob(S + '*.tsv'):
    last = {}
    for l in open(f):
        p = l.rstrip('\n').split('\t')
        fk = p[0]; ri, D, res = int(p[5]), int(p[6]), p[7]
        if ri not in last or D > last[ri][0]: last[ri] = (D, res)
    old[fk] = last
out = open('data/old_verdicts_final_u2.tsv', 'x')
for fk, last in old.items():
    out.write(fk + '\t' + ';'.join(f"{ri}:{D}:{res}" for ri, (D, res) in sorted(last.items())) + '\n')
out.close()
a64 = json.load(open('data/a_by_pattern.json'))
rows = [l.rstrip('\n').split('\t') for l in open(sys.argv[1])]
tab = collections.Counter(); dis = []
for r in rows:
    fk, s, M, a, y, nreps, nwords, verdict = r[:8]
    o = old[fk]
    maxD = max(D for D, _ in o.values())
    oldclass = 'sandwich' if any(res == 'CLOSED-sandwich' for _, res in o.values()) else 'cut'
    tab[(oldclass, maxD, verdict)] += 1
    if not verdict.startswith('CLOSED'): dis.append((fk, verdict))
    if a64[fk][2] >= 64: dis.append((fk, 'A>=64 input'))
print('patterns', len(rows), 'new-not-closed or A>=64 flagged:', dis)
for k in sorted(tab): print(k, tab[k])
