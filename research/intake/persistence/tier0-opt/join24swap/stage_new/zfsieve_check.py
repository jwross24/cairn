#!/usr/bin/env python3
"""check.py — exact check of zfsieve survivors: y = 2^a 3^b 7^c, digit count, zero-free. Incremental over out_*.txt."""
import sys, os, json, time
state_f = '/home/claude/zf/check_state.json'
st = json.load(open(state_f)) if os.path.exists(state_f) else {}
M = 10 ** 600
found = []; t0 = time.time(); n = 0; deep = 0
for res in (0, 1):
    f = f'/home/claude/zf/out_{res}.txt'
    if not os.path.exists(f): continue
    pos = st.get(f, 0)
    with open(f) as fh:
        fh.seek(pos)
        while True:
            line = fh.readline()
            if not line or not line.endswith('\n'): break
            pos = fh.tell()
            if line.startswith('DONE'): continue
            a, b, c = map(int, line.split()); n += 1
            if a * 0.30103 + b * 0.4771213 + c * 0.845098 > 602:          # ≥ 602 digits: the lowest 600 digits are genuine
                low = pow(2, a, M) * pow(3, b, M) * pow(7, c, M) % M
                if '0' in str(low).zfill(600): continue
            deep += 1
            y = 2 ** a * 3 ** b * 7 ** c; s = str(y)
            if '0' not in s: found.append((a, b, c, len(s)))
    st[f] = pos
json.dump(st, open(state_f, 'w'))
with open('/home/claude/zf/found.txt', 'a') as fo:
    for a, b, c, nd in found: fo.write(f"ZF-NEW {nd} {a} {b} {c}\n")
print(f"checked {n} survivors ({deep} needed the full check), found {len(found)} zero-free; total found so far: {sum(1 for _ in open('/home/claude/zf/found.txt')) if os.path.exists('/home/claude/zf/found.txt') else 0} [{time.time()-t0:.0f}s]")
