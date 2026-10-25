#!/usr/bin/env python3
"""Run an external implementation of the shadow certificate on per-representation JSON inputs and report agreement.

Input records (one per representation, produced by `cport_shadow shadow --dump F`):
  {"id", "modulus", "a", "nu", "min_digits", "digits":[{"d","e"}...], "upper_digits",
   "words":[{"id","fixed":[idx...],"offset":[b,c],"basis":[[..],[..]]}...]}
Mine (`--reps F`): tab-separated  id<TAB>verdict<TAB>min-squared-norm   verdict in CLOSED_CUT|CLOSED_SANDWICH|OPEN|...

  harness.py make   DUMP.jsonl PATTERNS.json              wrap the JSONL into the JSON array the external reads
  harness.py run    PATTERNS.json OUT.json -- CMD...      CMD reads PATTERNS.json on stdin (file redirect, not a pipe), writes JSON to stdout
  harness.py compare OUT.json MINE.tsv [--key verdict]     per-id agreement; exit 1 on any disagreement
The external output is a JSON array of objects with "id" and "verdict" (CLOSED_CUT|CLOSED_SANDWICH|OPEN|NOT_APPLICABLE);
optional fields compared when present: "dp_nonshadow_count".
"""
import json, subprocess, sys

def make(dump, out):
    recs = [json.loads(l) for l in open(dump) if l.strip()]
    json.dump(recs, open(out, 'x'))
    print(len(recs), 'records ->', out)

def run(pat, out, cmd):
    with open(pat) as fi, open(out, 'x') as fo:
        r = subprocess.run(cmd, stdin=fi, stdout=fo, stderr=subprocess.PIPE, text=True)
    print('rc', r.returncode, (r.stderr or '')[-500:])

def compare(out, mine):
    ext = {r['id']: r for r in json.load(open(out))}
    mv = {}
    for l in open(mine):
        p = l.rstrip('\n').split('\t'); mv[p[0]] = p[1]
    ids = sorted(set(ext) | set(mv))
    agree = 0; bad = []
    for i in ids:
        e = ext.get(i, {}).get('verdict'); m = mv.get(i)
        if e == m: agree += 1
        else: bad.append((i, m, e))
    print(f"{len(ids)} representations; agree {agree}; disagree {len(bad)}")
    for b in bad[:50]: print('DISAGREE id=%s mine=%s external=%s' % b)
    return 1 if bad else 0

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'make': make(sys.argv[2], sys.argv[3])
    elif c == 'run':
        k = sys.argv.index('--'); run(sys.argv[2], sys.argv[3], sys.argv[k + 1:])
    elif c == 'compare': sys.exit(compare(sys.argv[2], sys.argv[3]))
    else: sys.exit('usage')
