import re, sys

wl_files, mine_path = sys.argv[1:-1], sys.argv[-1]
wl = {}
for p in wl_files:
    for l in open(p):
        m = re.match(r"s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\S+)\s+k=(\d+) \[(.*)\] -> (CLOSED-cut|CLOSED-sandwich|open)(?: bound 10\^\(10\^([0-9.]+)\))?", l)
        if not m:
            continue
        s, M, a, y, k, log, verdict, bound = m.groups()
        reps = re.findall(r"\((\d+), 'T', (\d+), 'alive', (\d+)\)", log)
        wl[(s, M, a, y)] = (verdict, bound, sorted((int(w), int(t), int(al)) for w, t, al in reps))

mine = {}
for l in open(mine_path):
    m = re.match(r"s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\S+)\s+k=(\d+) log10 U=\S+ reps=\d+ words=\d+ -> (CLOSED-cut|CLOSED-sandwich|open)(?: bound 10\^\(10\^([0-9.]+))? (.*) alive=", l)
    if not m:
        continue
    s, M, a, y, k, verdict, bound, det = m.groups()
    reps = re.findall(r"\(w=(\d+),T=(\d+),G=\d+,compat=\d+,chain=\d+,win=\d+,alive=(\d+)", det)
    mine[(s, M, a, y)] = (verdict, bound, sorted((int(w), int(t), int(al)) for w, t, al in reps))

print('wordlift480 patterns', len(wl), 'mine', len(mine), 'common', len(set(wl) & set(mine)))
bad = 0
maxd = 0.0
for key in sorted(set(wl) & set(mine)):
    wv, wb, wr = wl[key]
    mv, mb, mr = mine[key]
    d = abs(float(wb) - float(mb)) if wb and mb else 0.0
    maxd = max(maxd, d)
    ok = wv == mv and wr == mr and (wb is None) == (mb is None) and d <= 0.051
    if not ok:
        bad += 1
        print('DIFF', key, wl[key], mine[key])
print('differences', bad, 'max |bound diff| (log10 digits, 1-decimal vs 2-decimal)', round(maxd, 3))
vc = {}
for v in wl.values():
    vc[v[0]] = vc.get(v[0], 0) + 1
print('wordlift480 verdict counts', vc)
vc = {}
for v in mine.values():
    vc[v[0]] = vc.get(v[0], 0) + 1
print('mine verdict counts', vc)
sys.exit(1 if bad else 0)
