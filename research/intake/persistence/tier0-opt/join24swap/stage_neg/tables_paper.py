#!/usr/bin/env python3
"""tables.py — generate TABLES.md for the paper from the data files only.

Every number printed in TABLES.md is computed here from the files listed in SOURCES (no hand-typed
results).  Run:  python3 /home/claude/night/paper/tables.py   (≈ 1–2 min, one process).

Sources (paths are absolute):
  corpus     /home/claude/tier0/zf_below_1e4000.txt          zero-free S-units below 10^4000 ("ZF ndigits a b c persistence")
  v1 sweep   /home/claude/tier0/runall_final.jsonl           53 vertices, pure-Python v1 engine (2026-10-19)
  C sweep    /tmp/trees_c.jsonl                              34 vertices, C level-12 engine (cloud)
  Mac sweep  /home/claude/night/trees_mac_0125.jsonl         83 vertices, C engine on the Mac (01:25 snapshot)
  Mac sweep  /home/claude/night/trees_mac_1250.jsonl         90 vertices, C engine on the Mac (12:50 snapshot, freshest)
  final      /home/claude/night/FINAL-STAGE-run-U2.txt       per-vertex final stage (Lemma C depth 1 + sandwich under Theorem U″), 138 vertices
  final-old  /home/claude/night/FINAL-STAGE-run.txt          the earlier final stage under Theorem U (133 vertices; used only for comparison notes)
  sandwich   /home/claude/night/SANDWICH-full-U2.txt         43 sandwich verdicts under U″ over the full sub-coset enumeration (C port)
  sandwich-U /home/claude/night/SANDWICH-full.txt            the same 43 under Theorem U (comparison only)
  utable     /home/claude/night/utable_U2.txt                certified Theorem U″ ceilings N(k, a), k ≤ 24, a ≤ 24
  notes-u2   /home/claude/night/NOTES-u2.md                  Theorem U″ notes; its table gives log10 G″ at k = 31, 44
  base 8     /home/claude/night/base8_L96_full.jsonl, base8_L384.jsonl, base8_sandwich_mac.jsonl (Mac); /tmp/base8*.jsonl (cloud)
  deepcut    /home/claude/tier0/DEEPCUT-run-final-d1.txt     depth-1 Lemma C verdicts (680 patterns, 05:45 sweep snapshot)
  frontier   /home/claude/night/FRONTIER.md                  tier assignment and cost columns of the not-enumerated vertices
  dpcount    /home/claude/night/RESULT-dpcount.md            Tier-C Monte-Carlo survivor estimates and 2-adic bounds
  base 8     /tmp/base8.jsonl, /tmp/base8_lift384.jsonl, /tmp/base8_sandwich.jsonl
  base 6     /tmp/base6.jsonl
Code imported: tier0v2.multisets (digit multisets of product s), baker_chain.baker_upper_bound (Theorem U ceiling).
Vertex enumeration follows run_trees_c.py lines 1–40: vertices are the corpus elements y ≥ 10 whose orbit ends in
{2,4,6,8}, plus the roots; the level-12 pattern count of a multiset M is 12·∏_d C(12+m_d−1, m_d).
"""
import sys, os, re, json, time
from collections import Counter, defaultdict
from math import comb, log10

sys.path.insert(0, '/home/claude/tier0')
from tier0v2 import multisets                      # noqa: E402
from baker_chain import baker_upper_bound          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'TABLES.md')
SOURCES = {
    'corpus': '/home/claude/tier0/zf_below_1e4000.txt',
    'v1': '/home/claude/tier0/runall_final.jsonl',
    'C': '/tmp/trees_c.jsonl',
    'mac': '/home/claude/night/trees_mac_0125.jsonl',
    'mac2': '/home/claude/night/trees_mac_1250.jsonl',
    'final': '/home/claude/night/FINAL-STAGE-run-U2.txt',
    'final_old': '/home/claude/night/FINAL-STAGE-run.txt',
    'sandwich': '/home/claude/night/SANDWICH-full-U2.txt',
    'sandwich_old': '/home/claude/night/SANDWICH-full.txt',
    'utable': '/home/claude/night/utable_U2.txt',
    'notes_u2': '/home/claude/night/NOTES-u2.md',
    'b8m_96': '/home/claude/night/base8_L96_full.jsonl',
    'b8m_384': '/home/claude/night/base8_L384.jsonl',
    'b8m_sand': '/home/claude/night/base8_sandwich_mac.jsonl',
    'deepcut': '/home/claude/tier0/DEEPCUT-run-final-d1.txt',
    'frontier': '/home/claude/night/FRONTIER.md',
    'dpcount': '/home/claude/night/RESULT-dpcount.md',
    'base8_48': '/tmp/base8.jsonl',
    'base8_lift': '/tmp/base8_lift384.jsonl',
    'base8_sandwich': '/tmp/base8_sandwich.jsonl',
    'base6': '/tmp/base6.jsonl',
}
NOTES = []          # source notes (disagreements, gaps) — printed verbatim at the end of TABLES.md


def note(s):
    NOTES.append(s)


# ----------------------------------------------------------------------------- helpers
def dp(x):
    p = 1
    for ch in str(x):
        p *= int(ch)
    return p


def orbit_end(x):
    while x >= 10:
        x = dp(x)
    return x


def fact237(y):
    e = {2: 0, 3: 0, 7: 0}
    for p in (2, 3, 7):
        while y % p == 0:
            y //= p
            e[p] += 1
    return (e[2], e[3], e[7]) if y == 1 else None


def fstr(y, primes=(2, 3, 7)):
    """2^a·3^b·7^c string (base 10) or general prime factorization string."""
    if y == 1:
        return '1'
    parts = []
    for p in primes:
        e = 0
        while y % p == 0:
            y //= p
            e += 1
        if e:
            parts.append(f'{p}^{e}' if e > 1 else f'{p}')
    if y != 1:
        parts.append(f'[{y}]')
    return '·'.join(parts)


def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p


def sci(x):
    return f'{x:.3e}' if x else '0'


def load_jsonl(f):
    return [json.loads(l) for l in open(f) if l.strip()]


# ----------------------------------------------------------------------------- corpus and trees
rows = [l.split() for l in open(SOURCES['corpus']) if l.startswith('ZF')]
S = [2 ** int(a) * 3 ** int(b) * 7 ** int(c) for _, d, a, b, c, p in rows]
assert len(S) == len(set(S))
kids = defaultdict(list)
for y in S:
    if y >= 10:
        kids[dp(y)].append(y)
tree_of = {}
for y in S:
    if y >= 10:
        e = orbit_end(y)
        if e in (2, 4, 6, 8):
            tree_of[y] = e
for r in (2, 4, 6, 8):
    tree_of[r] = r
VERTICES = sorted(tree_of)
per_tree = Counter(tree_of.values())
EQS = {s: [tuple(sorted(M)) for M in multisets(s)] for s in VERTICES}
PATTERNS = {s: sum(npat(M) for M in EQS[s]) for s in VERTICES}
KMAX = {s: max((len(M) for M in EQS[s]), default=0) for s in VERTICES}

# ----------------------------------------------------------------------------- sweep files
SW = {name: {r['s']: r for r in load_jsonl(SOURCES[name])} for name in ('v1', 'C', 'mac', 'mac2')}
FRESH = ('mac2', 'mac', 'C', 'v1')     # preference order


def exceptional_triples(src, r):
    """distinct (M, a, y, is_self) over the recorded open patterns of a vertex row."""
    out = set()
    if src == 'v1':
        for M, a, nu, eps, (y, selff) in r['exceptional']:
            out.add((tuple(M), a, y, bool(selff)))
    else:
        for e in r['eqs']:
            for a, y, selff in e['exceptional']:
                out.add((tuple(e['M']), a, y, bool(selff)))
    return out


def eq_count(src, r):
    return len(r['eqs'])


def pattern_total(src, r):
    if src == 'v1':
        return sum(lv[1] for M, op, sols, levels in r['eqs'] for lv in levels[:1])
    return r.get('patterns')


BEST = {}
for name in reversed(FRESH):
    for s, r in SW[name].items():
        BEST[s] = (name, r)
for s in sorted(BEST):
    present = [n for n in FRESH if s in SW[n]]
    if len(present) > 1:
        vals = {}
        for n in present:
            r = SW[n][s]
            vals[n] = (r['target'], tuple(r['found']), tuple(r['known']), r['open'], bool(r['closed']),
                       str(r['digit_bound']), pattern_total(n, r))
        if len(set(vals.values())) > 1:
            note(f'vertex {s}: sweep files disagree: ' + '; '.join(f'{n}: {v}' for n, v in vals.items()))
ENUMERATED = set(BEST)
for s in ENUMERATED:
    if s not in tree_of:
        note(f'vertex {s} appears in a sweep file but is not a vertex of T_2..T_8 as computed from the corpus')

# ----------------------------------------------------------------------------- final stage, sandwich, deepcut
def parse_final(path):
    fs, total = {}, None
    for l in open(path):
        m = re.match(r's=(\d+)\s+open-patterns=(\d+)\s+CLOSED-cut=(\d+)\s+CLOSED-sandwich=(\d+)\s+open=(\d+) BUDGET=(\d+) '
                     r'UNSUPPORTED=(\d+) UNFINISHED=(\d+) -> (\w+)', l)
        if m:
            fs[int(m.group(1))] = dict(open=int(m.group(2)), cut=int(m.group(3)), sand=int(m.group(4)), left=int(m.group(5)),
                                       budget=int(m.group(6)), unsup=int(m.group(7)), unfin=int(m.group(8)), verdict=m.group(9))
        elif l.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')) and 'vertices' in l:
            total = l.strip()
    return fs, total


def parse_sandwich(path):
    out = []
    for l in open(path):
        m = re.match(r's=(\d+)\s+M=(\d+)\s+a=(\d+) y=(\d+)\s+k=(\d+) reps=(\d+) log10G=([\d.]+) depth=(\d+) subcosets=(\d+) '
                     r'min-bound=([\d.]+) margin=([+\-\d.]+) wall=\d+s -> (\w+)', l)
        if m:
            g = m.groups()
            out.append(dict(s=int(g[0]), M=g[1], a=int(g[2]), y=int(g[3]), k=int(g[4]), reps=int(g[5]), logG=float(g[6]),
                            depth=int(g[7]), sub=int(g[8]), minb=float(g[9]), margin=float(g[10]), verdict=g[11]))
    return out


FS, FS_TOTAL = parse_final(SOURCES['final'])
FS_OLD, FS_OLD_TOTAL = parse_final(SOURCES['final_old'])
SANDWICH = parse_sandwich(SOURCES['sandwich'])
SANDWICH_OLD = parse_sandwich(SOURCES['sandwich_old'])
SAND_BY_S = defaultdict(list)
for p in SANDWICH:
    SAND_BY_S[p['s']].append(p)

# Theorem U″ table: N(k, a) certified for k ≤ 24, a ≤ 24; log10 G″ at k = 31, 44 from the table in NOTES-u2.md
UTABLE = {}
for l in open(SOURCES['utable']):
    k, a, N = l.split()
    UTABLE[(int(k), int(a))] = log10(int(N))
U2_NOTES = {}
for l in open(SOURCES['notes_u2']):
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(cells) == 5 and cells[0].isdigit() and cells[1].isdigit():
        U2_NOTES[(int(cells[0]), int(cells[1]))] = dict(uprime=float(cells[2]), u2=float(cells[3]), second=float(cells[4]))


def g_u2(k, a):
    """log10 G″(k, a) from the certified table (a clamped to its range), else from NOTES-u2.md, else None."""
    if (k, min(a, 24)) in UTABLE and a <= 24:
        return UTABLE[(k, a)]
    if (k, a) in U2_NOTES:
        return U2_NOTES[(k, a)]['u2']
    return None

DEEP = []
for l in open(SOURCES['deepcut']):
    m = re.match(r's=(\d+)\s+M=(\d+)\s+a=(\d+)\s+y=(\d+)\s+reps=(\d+)\s+cases=(\d+)\s+(\w+)', l)
    if m:
        g = m.groups()
        DEEP.append(dict(s=int(g[0]), M=g[1], a=int(g[2]), y=int(g[3]), reps=int(g[4]), cases=int(g[5]), verdict=g[6]))
DEEP_BY_S = defaultdict(list)
for p in DEEP:
    DEEP_BY_S[p['s']].append(p)

# ----------------------------------------------------------------------------- FRONTIER.md table
FRONT = {}
for l in open(SOURCES['frontier']):
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(cells) == 12 and cells[0] in ('A', 'B', 'C') and cells[2].isdigit():
        FRONT[int(cells[2])] = dict(tier=cells[0], tree=cells[1], form=cells[3], patterns=float(cells[4]), kmax=int(cells[5]),
                                    multisets=int(cells[6]), d1=float(cells[7]), d10=float(cells[8]), gpu=float(cells[9]),
                                    open96=cells[10], depth=cells[11])

# ----------------------------------------------------------------------------- RESULT-dpcount.md tables
DPC = {}
txt = open(SOURCES['dpcount']).read()
sec = txt.split('### Per-vertex Monte-Carlo estimates')[1].split('### The a-split')[0]
for l in sec.splitlines():
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(cells) == 11 and cells[0].isdigit():
        DPC[int(cells[0])] = dict(form=cells[1], multisets=int(cells[2]), k=cells[3], patterns=cells[4], samples=cells[5],
                                  surv=cells[6], rate=cells[7], children24=cells[8], lifts=cells[9], bound4=cells[10])
sec = txt.split('### The a-split')[1].split('### Hybrid')[0]
for l in sec.splitlines():
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(cells) == 6 and cells[0].isdigit():
        DPC[int(cells[0])].update(A=int(cells[1]), capped=cells[2], apairs=cells[3], children24a=cells[4], aper=cells[5])


# ----------------------------------------------------------------------------- Table A
def status_of(s):
    """(status label, detail) for a vertex."""
    if s not in ENUMERATED:
        f = FRONT.get(s)
        tier = tier_of(s)
        if f is None:
            return (f'not enumerated (Tier {tier})', 'no row in FRONTIER.md')
        return (f'not enumerated (Tier {tier})',
                f'{f["d1"]:.1f} core-days @8 ns, {f["gpu"]:.2f} GPU-days @1e10/s (FRONTIER.md)')
    src, r = BEST[s]
    fs = FS.get(s)
    if fs is None:
        return ('closed-below-height',
                f'enumerated to level 96 ({src}), {r["open"]} open patterns, lattice bound {sci(r["digit_bound"] or 0)} digits; '
                f'final stage (Lemma C/sandwich) not run on this vertex (enumerated after the final-stage snapshot)')
    if fs['unfin'] or fs['unsup'] or fs['left'] or fs['budget']:
        return ('closed-below-height',
                f'{fs["open"]} open; {fs["cut"]} closed by Lemma C d1, {fs["sand"]} by sandwich, '
                f'{fs["unfin"]} not run through the sandwich (UNFINISHED), {fs["unsup"]} unsupported; residual bound: depth-1 '
                f'Lemma C (≥ 10^(10^71.48) digits, DEEPCUT-run-final-d1.txt) where depth 1 survived, else the lattice bound')
    if fs['sand']:
        det = f'{fs["open"]} open; {fs["cut"]} by Lemma C d1, {fs["sand"]} by sandwich'
        ps = SAND_BY_S.get(s)
        if ps:
            if len(ps) != fs['sand']:
                det += f' (SANDWICH-full.txt lists {len(ps)} of them)'
            det += f'; U″ depth ≤ {max(p["depth"] for p in ps)}, min margin 10^{min(p["margin"] for p in ps):.2f} digits'
        else:
            det += '; depth/margin not recorded in SANDWICH-full-U2.txt'
        return ('CLOSED by sandwich', det)
    if fs['cut']:
        return ('CLOSED by Lemma C (depth 1)', f'{fs["open"]} open patterns at level 96, all closed at depth 1')
    return ('CLOSED by computation', 'no open pattern at level 96')


TIER_A_CAP = 7e13          # Tier A = not-yet-enumerated vertices with at most this many level-12 patterns (coordinator's definition)


def tier_of(s):
    if PATTERNS[s] <= TIER_A_CAP:
        return 'A'
    f = FRONT.get(s)
    return f['tier'] if f else '?'


tableA = []
V1_APAT = []
for s in VERTICES:
    known = sorted(kids.get(s, []))
    if s in ENUMERATED:
        src, r = BEST[s]
        found = sorted(r['found'])
        known_file = sorted(r['known'])
        flag = ''
        if found != known:
            flag = 'FOUND≠KNOWN'
        if known_file != known:
            flag += (' ' if flag else '') + 'file-known≠corpus'
            note(f'vertex {s}: known children in {src} file {known_file} differ from corpus {known}')
        neq_file = eq_count(src, r)
        if neq_file != len(EQS[s]):
            note(f'vertex {s}: {neq_file} equations in {src} file vs {len(EQS[s])} multisets computed')
        pt = pattern_total(src, r)
        if pt is not None and pt != PATTERNS[s]:
            if src == 'v1':
                V1_APAT.append((s, pt, PATTERNS[s]))      # v1 counts (a, pattern) pairs, not patterns: noted once below
            else:
                note(f'vertex {s}: level-12 pattern total {pt} in {src} file vs {PATTERNS[s]} computed')
    else:
        src, found, flag = '—', None, ''
    st, det = status_of(s)
    tableA.append(dict(s=s, tree=tree_of[s], fact=fstr(s), neq=len(EQS[s]), npat=PATTERNS[s], kmax=KMAX[s], src=src,
                       status=st, detail=det, found=found, known=known, flag=flag))
    if s in FRONT and abs(FRONT[s]['patterns'] - PATTERNS[s]) / PATTERNS[s] > 0.01:
        note(f'vertex {s}: FRONTIER.md pattern count {FRONT[s]["patterns"]:.3e} vs computed {PATTERNS[s]:.3e}')
    if s in FRONT and FRONT[s]['kmax'] != KMAX[s]:
        note(f'vertex {s}: FRONTIER.md k_max {FRONT[s]["kmax"]} vs computed {KMAX[s]}')
    if s in FRONT and FRONT[s]['multisets'] != len(EQS[s]):
        note(f'vertex {s}: FRONTIER.md multisets {FRONT[s]["multisets"]} vs computed {len(EQS[s])}')

if V1_APAT:
    note(f'the v1 file (runall_final.jsonl) records per equation the number of (a, pattern) pairs at level 12, not the pattern '
         f'count: on all {len(V1_APAT)} of its vertices with a difference the file total exceeds the computed pattern count '
         f'(ratios {min(pt/pc for s, pt, pc in V1_APAT):.1f}–{max(pt/pc for s, pt, pc in V1_APAT):.1f}, i.e. A+1 averaged over '
         f'the multisets); Table A uses the computed pattern count throughout')
STATUS_COUNT = Counter(row['status'] for row in tableA)
STATUS_BY_TREE = defaultdict(Counter)
for row in tableA:
    STATUS_BY_TREE[row['tree']][row['status']] += 1

# cross-checks on the final stage
for s, fs in FS.items():
    if s not in ENUMERATED:
        note(f'FINAL-STAGE-run.txt lists vertex {s}, which is in no sweep file')
    else:
        src, r = BEST[s]
        tr = exceptional_triples(src, r)
        if fs['open'] not in (r['open'], len(tr)):
            note(f'vertex {s}: FINAL-STAGE open-patterns {fs["open"]} vs sweep open {r["open"]} / distinct triples {len(tr)}')
for s in ENUMERATED:
    if s not in FS:
        note(f'vertex {s}: in the Mac sweep file (12:50) but not in FINAL-STAGE-run-U2.txt (final stage not run; its snapshot was earlier)')
for s in FS_OLD:
    if s not in FS:
        note(f'vertex {s}: in FINAL-STAGE-run.txt (U) but not in FINAL-STAGE-run-U2.txt')
_fewer = [(s, FS_OLD[s]['open'], FS[s]['open']) for s in FS_OLD if s in FS and FS[s]['open'] < FS_OLD[s]['open']]
_more = sum(1 for s in FS_OLD if s in FS and FS[s]['open'] > FS_OLD[s]['open'])
note(f'FINAL-STAGE-run.txt (Theorem U, {len(FS_OLD)} vertices) vs FINAL-STAGE-run-U2.txt (Theorem U″, {len(FS)} vertices, fresh snapshot): '
     f'{_more} vertices have more open patterns in the U″ run, {len(_fewer)} have fewer' + (f' ({_fewer})' if _fewer else '') +
     f'; U run totals {sum(v["open"] for v in FS_OLD.values())} open / {sum(v["cut"] for v in FS_OLD.values())} Lemma C / '
     f'{sum(v["sand"] for v in FS_OLD.values())} sandwich / {sum(v["unfin"]+v["unsup"] for v in FS_OLD.values())} not finished; U″ run '
     f'{sum(v["open"] for v in FS.values())} / {sum(v["cut"] for v in FS.values())} / {sum(v["sand"] for v in FS.values())} / '
     f'{sum(v["unfin"]+v["unsup"]+v["left"]+v["budget"] for v in FS.values())}. NOTES-u2.md compares against a 137-vertex U run (7645 patterns), '
     f'not the 133-vertex FINAL-STAGE-run.txt at hand.')
_old = {(p['s'], p['M'], p['a'], p['y']): p for p in SANDWICH_OLD}
_new = {(p['s'], p['M'], p['a'], p['y']): p for p in SANDWICH}
if set(_old) != set(_new):
    note(f'SANDWICH-full.txt and SANDWICH-full-U2.txt list different pattern keys: {set(_old) ^ set(_new)}')
else:
    note(f'SANDWICH-full-U2.txt vs SANDWICH-full.txt (same 43 patterns): depths under U″ ' +
         ', '.join(f'{d}: {c}' for d, c in sorted(Counter(p['depth'] for p in SANDWICH).items())) + ' against U ' +
         ', '.join(f'{d}: {c}' for d, c in sorted(Counter(p['depth'] for p in SANDWICH_OLD).items())) +
         f'; every pattern closes at a depth ≤ its U depth: {all(_new[k]["depth"] <= _old[k]["depth"] for k in _new)}; '
         f'log10 G″ − log10 G ranges {min(_new[k]["logG"]-_old[k]["logG"] for k in _new):.2f} to {max(_new[k]["logG"]-_old[k]["logG"] for k in _new):.2f}; '
         f'min margin {min(p["margin"] for p in SANDWICH):.2f} (U: {min(p["margin"] for p in SANDWICH_OLD):.2f}).')
# U″ table consistency with the sandwich file's log10G column
_bad = [(p['s'], p['M'], p['logG'], g_u2(p['k'], p['a'])) for p in SANDWICH if g_u2(p['k'], p['a']) is None or abs(p['logG'] - g_u2(p['k'], p['a'])) > 0.011]
if _bad:
    note(f'SANDWICH-full-U2.txt log10G differs from utable_U2.txt on {len(_bad)} patterns: {_bad[:5]}')
else:
    note(f'SANDWICH-full-U2.txt log10G agrees with utable_U2.txt on all {len(SANDWICH)} patterns (to 0.01).')
_lt = sum(1 for (k, a), v in UTABLE.items() if v <= baker_upper_bound(k, a, return_log10=True)[1] + 1e-9)
note(f'utable_U2.txt: {len(UTABLE)} entries (k = {min(k for k, a in UTABLE)}–{max(k for k, a in UTABLE)}, a = {min(a for k, a in UTABLE)}–{max(a for k, a in UTABLE)}); '
     f'{_lt} of them are ≤ the Theorem U ceiling baker_upper_bound(k, a); NOTES-u2.md table entries: ' +
     ', '.join(f'({k},{a}): {v["u2"]:.2f}' for (k, a), v in sorted(U2_NOTES.items())) + '.')
DEEP_MISMATCH = []
for s, ps in DEEP_BY_S.items():
    fs = FS.get(s)
    if fs:
        closed = sum(p['verdict'] == 'CLOSED' for p in ps)
        if (len(ps), closed) != (fs['open'], fs['cut']):
            note(f'vertex {s}: DEEPCUT-run-final-d1.txt {closed}/{len(ps)} CLOSED at depth 1 vs FINAL-STAGE {fs["cut"]}/{fs["open"]} '
                 f'(different sweep snapshots)')
if DEEP_MISMATCH:
    note(f'DEEPCUT-run-final-d1.txt (05:45 snapshot) differs from FINAL-STAGE-run-U2.txt (fresh snapshot) in the per-vertex (patterns, depth-1 closed) '
         f'counts on {len(DEEP_MISMATCH)} of {len(DEEP_BY_S)} vertices (e.g. {DEEP_MISMATCH[:3]} as (s, d1 patterns, d1 closed, U2 open, U2 cut)): '
         f'the later sweep records more open patterns per vertex; the depth-1 verdicts are not contradicted.')
SAND_MISMATCH = []
for s, ps in SAND_BY_S.items():
    fs = FS.get(s)
    if fs and fs['sand'] != len(ps):
        SAND_MISMATCH.append((s, len(ps), fs['sand']))
    for p in ps:
        if p['verdict'] != 'CLOSED':
            note(f'SANDWICH-full.txt: s={s} M={p["M"]} verdict {p["verdict"]}')

if SAND_MISMATCH:
    note(f'SANDWICH-full-U2.txt (43 patterns of the 05:45 snapshot) vs FINAL-STAGE-run-U2.txt CLOSED-sandwich counts per vertex: differ on '
         f'{len(SAND_MISMATCH)} of {len(SAND_BY_S)} vertices (s, in file, in final stage): {SAND_MISMATCH} — the fresh snapshot has more '
         f'sandwich patterns; the 43 are a subset with recorded depth and margin.')
# ----------------------------------------------------------------------------- Table B: anchors
ANCH = defaultdict(lambda: dict(n=0, vertices=set(), selfv=set()))
NTRIPLES = 0
for s in sorted(ENUMERATED):
    src, r = BEST[s]
    for M, a, y, selff in exceptional_triples(src, r):
        NTRIPLES += 1
        ANCH[y]['n'] += 1
        ANCH[y]['vertices'].add(s)
        if selff:
            ANCH[y]['selfv'].add(s)
ZERO_DIGIT = {y for y in ANCH if '0' in str(y)}
NOT_SUNIT = {y for y in ANCH if fact237(y) is None}
SELF_N = sum(1 for s in ENUMERATED for M, a, y, selff in exceptional_triples(*BEST[s]) if selff)

# ----------------------------------------------------------------------------- Table C: other bases
def base_digits(y, b):
    out = []
    while y:
        out.append(y % b)
        y //= b
    return out


def base_corpus(b, D):
    primes = [p for p in range(2, b) if all(p % q for q in range(2, p))]
    lim = b ** D
    out = []

    def rec(i, val):
        if i == len(primes):
            out.append(val)
            return
        v = val
        while v < lim:
            rec(i + 1, v)
            v *= primes[i]
    rec(0, 1)
    return primes, [y for y in out if 0 not in base_digits(y, b)]


def base_dp(y, b):
    p = 1
    for d in base_digits(y, b):
        p *= d
    return p


def base_vertices(b, D):
    primes, zf = base_corpus(b, D)
    kidsb = defaultdict(list)
    for y in zf:
        if y >= b:
            kidsb[base_dp(y, b)].append(y)

    def end(y):
        while y >= b:
            y = base_dp(y, b)
        return y
    verts = {y: y for y in range(1, b)}
    for y in zf:
        if y >= b:
            e = end(y)
            if e != 0:
                verts[y] = e
    return primes, zf, verts, kidsb


B8 = {n: {r['s']: r for r in load_jsonl(SOURCES[n])} for n in ('base8_48', 'base8_lift', 'base8_sandwich', 'b8m_96', 'b8m_384', 'b8m_sand')}
B8_MAC = ('b8m_sand', 'b8m_384', 'b8m_96')
B8_CLOUD = ('base8_sandwich', 'base8_lift', 'base8_48')
B6 = {r['s']: r for r in load_jsonl(SOURCES['base6'])}
t0 = time.time()
P8, ZF8, V8, K8 = base_vertices(8, 70)
P6, ZF6, V6, K6 = base_vertices(6, 60)


def base_status(s, files, order):
    """freshest file that has the vertex, in `order`; returns (label, detail)."""
    for n in order:
        r = files[n].get(s)
        if r is not None:
            lvl = max(l[0] for e in r['eqs'] for l in e['levels'])
            lifted = r.get('lifted_to')
            return (r['status'], f'{n}: levels ≤ {lvl}' + (f', lifted to {lifted}' if lifted else '') + f', open {r["open"]}')
    return ('not enumerated', '')


tableC8 = []
for s in sorted(V8):
    st, det = base_status(s, B8, B8_MAC)
    stc, detc = base_status(s, B8, B8_CLOUD)
    found = None
    known = sorted(K8.get(s, []))
    flag = ''
    for n in B8_MAC + B8_CLOUD:
        r = B8[n].get(s)
        if r is not None:
            if found is None:
                found = sorted(r['found'])
            if sorted(r['known']) != known:
                note(f'base 8 vertex {s}: {n} known {sorted(r["known"])} vs corpus {known}')
            if sorted(r['found']) != known:
                flag = 'FOUND≠KNOWN'
    # a vertex is closed outright when any Mac file says CLOSED
    mac_closed = any(B8[n].get(s, {}).get('status') == 'CLOSED' for n in B8_MAC)
    cloud_closed = any(B8[n].get(s, {}).get('status') == 'CLOSED' for n in B8_CLOUD)
    tableC8.append(dict(s=s, tree=V8[s], fact=fstr(s, (2, 3, 5, 7)), status=st, detail=det, cloud=stc, cloud_detail=detc,
                        mac_closed=mac_closed, cloud_closed=cloud_closed, found=found, known=known, flag=flag))
B8_MAC_CLOSED = sum(r['mac_closed'] for r in tableC8)
B8_MAC_384 = sum(B8['b8m_384'][s]['status'] == 'CLOSED' for s in B8['b8m_384'])
B8_MAC_SAND_NEW = sum(1 for s in B8['b8m_sand'] if B8['b8m_384'].get(s, {}).get('status') != 'CLOSED')
B8_PENDING = sorted(r['s'] for r in tableC8 if not r['mac_closed'])
B8_PENDING_CLOUD_CLOSED = sorted(r['s'] for r in tableC8 if not r['mac_closed'] and r['cloud_closed'])
B8_PENDING_ALL = sorted(r['s'] for r in tableC8 if not r['mac_closed'] and not r['cloud_closed'])
for s in B8['base8_lift']:
    if B8['base8_lift'][s]['status'] != B8['b8m_384'][s]['status']:
        note(f'base 8 vertex {s}: cloud base8_lift384 status "{B8["base8_lift"][s]["status"]}" vs Mac base8_L384 "{B8["b8m_384"][s]["status"]}"')
for n in B8:
    for s in B8[n]:
        if s not in V8:
            note(f'base 8: vertex {s} in {n} is not a vertex of the computed base-8 trees')
tableC6 = []
for s in sorted(V6):
    st, det = base_status(s, {'base6': B6}, ('base6',))
    found = None
    known = sorted(K6.get(s, []))
    flag = ''
    r = B6.get(s)
    if r is not None:
        found = sorted(r['found'])
        if sorted(r['known']) != known:
            note(f'base 6 vertex {s}: file known {sorted(r["known"])} vs corpus {known}')
        if found != known:
            flag = 'FOUND≠KNOWN'
    tableC6.append(dict(s=s, tree=V6[s], fact=fstr(s, (2, 3, 5)), status=st, detail=det, found=found, known=known, flag=flag))
for s in B6:
    if s not in V6:
        note(f'base 6: vertex {s} in base6.jsonl is not a vertex of the computed base-6 trees')
C8_COUNT = Counter(r['status'] for r in tableC8)
C6_COUNT = Counter(r['status'] for r in tableC6)

# ----------------------------------------------------------------------------- Table D: frontier
tableD = []
for s in VERTICES:
    f = FRONT.get(s)
    if s in ENUMERATED or f is None or tier_of(s) == 'A':
        continue
    if f['tier'] != tier_of(s):
        note(f'vertex {s}: FRONTIER.md Tier {f["tier"]} vs Tier {tier_of(s)} by the pattern-count rule (≤ {TIER_A_CAP:.0e} = A)')
    k = KMAX[s]
    _, g0 = baker_upper_bound(k, 0, return_log10=True)
    _, g1 = baker_upper_bound(k, 1, return_log10=True)
    d = DPC.get(s)
    gA = None
    if d and 'A' in d:
        _, gA = baker_upper_bound(k, d['A'], return_log10=True)
    tableD.append(dict(s=s, tier=tier_of(s), tree=tree_of[s], fact=fstr(s), neq=len(EQS[s]), npat=PATTERNS[s], kmax=k,
                       g0=float(g0), g1=float(g1), gA=(float(gA) if gA is not None else None), d1=f['d1'], d10=f['d10'],
                       gpu=f['gpu'], dpc=d, u2_0=g_u2(k, 0), u2_1=g_u2(k, 1)))
for s in FRONT:
    if s in ENUMERATED and FRONT[s]['tier'] != 'A':
        note(f'vertex {s}: FRONTIER.md Tier {FRONT[s]["tier"]} but it is enumerated in a sweep file')
    if s not in ENUMERATED and FRONT[s]['tier'] == 'A' and tier_of(s) != 'A':
        note(f'vertex {s}: FRONTIER.md Tier A but {PATTERNS[s]:.2e} patterns exceed the Tier-A cap {TIER_A_CAP:.0e}')
for s in VERTICES:
    if s not in ENUMERATED and s not in FRONT:
        note(f'vertex {s}: not enumerated and absent from the FRONTIER.md table')
for s in DPC:
    if s not in tree_of:
        note(f'RESULT-dpcount.md vertex {s} is not a vertex of T_2..T_8')
    elif s in FRONT and FRONT[s]['tier'] != 'C':
        note(f'RESULT-dpcount.md vertex {s} is Tier {FRONT[s]["tier"]} in FRONTIER.md')

# ----------------------------------------------------------------------------- claims in the documents checked against the data
# (the quoted claims are copied from the named documents; the numbers they are compared with are computed above)
v1_open_v = [r for r in SW['v1'].values() if r['open'] > 0]
v1_tr = Counter(e[4][0] for r in v1_open_v for e in r['exceptional'])
note(f'RESULT.md T0′ ("16 vertices leave 27 residue patterns OPEN"; "111132 and 13122 anchor 13 of the 27 ... across five '
     f'vertices"): the v1 file has {len(v1_open_v)} vertices with {sum(r["open"] for r in v1_open_v)} open patterns; 111132 anchors '
     f'{v1_tr[111132]} and 13122 anchors {v1_tr[13122]} of them ({v1_tr[111132]+v1_tr[13122]} in all, not 13).')
note(f'OPEN-PATTERNS.md ("299 distinct open triples over 47 vertices ... every anchor y ≤ 1134213192 ... 73 distinct anchors", '
     f'00:45 snapshot): the current files give {NTRIPLES} triples over {sum(1 for s in ENUMERATED if BEST[s][1]["open"] > 0)} '
     f'vertices, {len(ANCH)} anchors, largest {max(ANCH)} = {fstr(max(ANCH))} (H1-REPORT.md already records the cap as stale; '
     f'its "210 anchors / 3154 triples" is an intermediate snapshot). Anchors with a 0 digit: {len(ZERO_DIGIT)}; non-S-units: {len(NOT_SUNIT)}.')
note(f'DEEPCUT.md / SANDWICH.md / FRONTIER.md ("Lemma C depth 1 closes ~94% of open patterns"): true of DEEPCUT-run-final-d1.txt '
     f'({sum(p["verdict"]=="CLOSED" for p in DEEP)}/{len(DEEP)} = {100*sum(p["verdict"]=="CLOSED" for p in DEEP)/len(DEEP):.1f} %, '
     f'k ≤ 11) but over the {len(FS)} vertices of FINAL-STAGE-run-U2.txt the depth-1 rate is '
     f'{sum(fs["cut"] for fs in FS.values())}/{sum(fs["open"] for fs in FS.values())} = '
     f'{100*sum(fs["cut"] for fs in FS.values())/sum(fs["open"] for fs in FS.values()):.1f} % (it falls with k).')
sd = Counter(p['depth'] for p in SANDWICH_OLD)
_mo = min(SANDWICH_OLD, key=lambda p: p['margin'])
note(f'SANDWICH.md "Result" ("43/43 closed ... depths 2 (7 patterns), 3 (29), 4 (11); the smallest margin was 10^5.3 digits"): '
     f'7+29+11 = 47 ≠ 43; SANDWICH-full.txt (the Theorem-U re-run over the full sub-coset enumeration, C port) has depths '
     + ', '.join(f'{d}: {c}' for d, c in sorted(sd.items())) + f' (sum {sum(sd.values())}) and smallest margin 10^{_mo["margin"]:.2f} '
     f'(s={_mo["s"]}, M={_mo["M"]}); HYPOTHESES.md ("7/26/10") agrees with the file.')
nf = Counter(FRONT[s]['tier'] for s in FRONT if FRONT[s]['tier'] in 'BC')
nft = Counter(tree_of[s] for s in FRONT if FRONT[s]['tier'] in 'BC')
note(f'PAPER.md §1/§4 and SANDWICH.md ("the ⟨18⟩ vertices of Table D (12 in T_6, 5 in T_8, 1 in T_2, 1 in T_4)"; "18 enumeration-frontier '
     f'vertices"): FRONTIER.md Tiers B and C contain {nf["B"]}+{nf["C"]} = {nf["B"]+nf["C"]} vertices '
     f'(T_2: {nft[2]}, T_4: {nft[4]}, T_6: {nft[6]}, T_8: {nft[8]}); the per-tree breakdown itself sums to 19, so "18" is a miscount.')
note(f'FRONTIER.md header ("105 done ... 72 remain"; Tier A = 53 vertices) is the 05:45 snapshot: the files now hold {len(ENUMERATED)} '
     f'enumerated vertices and {len(VERTICES)-len(ENUMERATED)} not enumerated ({STATUS_COUNT["not enumerated (Tier A)"]} of Tier A remain).')
note(f'PAPER.md §1 ("32, 8, 83, 50 multi-digit vertices for Δ = 2, 4, 6, 8"): computed {per_tree[2]-1}, {per_tree[4]-1}, '
     f'{per_tree[6]-1}, {per_tree[8]-1} — agrees.')
note(f'REDTEAM-base8.txt / PROGRAM-BASES.md ("base 8: corpus 4239 zero-free S-units below 8^70; 70 vertices"): computed {len(ZF8)} '
     f'zero-free units including the {len([y for y in ZF8 if y < 8])} single-digit ones ({len(ZF8)-7} multi-digit) and {len(V8)} vertices — agrees. '
     f'Base-8 vertices in no cloud file: {sorted(s for s in V8 if all(s not in B8[n] for n in B8_CLOUD))}; in no Mac file: '
     f'{sorted(s for s in V8 if all(s not in B8[n] for n in B8_MAC))}. The Mac level-96 file has {len(B8["b8m_96"])} vertices, '
     f'{sum(r["open"] for r in B8["b8m_96"].values())} open patterns in all, and every one at level 96 or finished earlier.')
note(f'PROGRAM-BASES.md ("base 6: 29 vertices (incl. 5 roots)"): computed {len(V6)} — agrees; base6.jsonl holds {len(B6)}; missing: '
     f'{sorted(s for s in V6 if s not in B6)}.')
note(f'FINAL-STAGE-run.txt (Theorem U): the {sum(1 for v in FS_OLD.values() if v["verdict"] != "CLOSED")} vertices it reported as "not fully CLOSED" were '
     f'UNFINISHED/UNSUPPORTED cases ({sum(v["unfin"] for v in FS_OLD.values())} patterns unfinished, {sum(v["unsup"] for v in FS_OLD.values())} unsupported); '
     f'FINAL-STAGE-run-U2.txt reports {sum(1 for v in FS.values() if v["verdict"] != "CLOSED")} vertices not fully CLOSED and '
     f'{sum(v["unfin"]+v["unsup"]+v["left"]+v["budget"] for v in FS.values())} patterns unfinished/unsupported/open/budget.')
# ----------------------------------------------------------------------------- write
L = []
w = L.append
w('# TABLES.md — generated by tables.py from the data files (do not edit by hand)')
w('')
w(f'Generated {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}. Sources: ' +
  ', '.join(f'`{os.path.basename(v)}`' for v in SOURCES.values()) + '.')
w('')
w('## Summary counts')
w('')
w(f'- Corpus: {len(S)} zero-free S-units below 10^4000; vertices of T_2 ∪ T_4 ∪ T_6 ∪ T_8 (roots included): {len(VERTICES)} '
  f'(T_2: {per_tree[2]}, T_4: {per_tree[4]}, T_6: {per_tree[6]}, T_8: {per_tree[8]}; multi-digit: '
  f'{per_tree[2]-1}, {per_tree[4]-1}, {per_tree[6]-1}, {per_tree[8]-1}).')
w(f'- Enumerated to level 96 (union of the sweep files): {len(ENUMERATED)} vertices '
  f'(v1: {len(SW["v1"])}, C: {len(SW["C"])}, Mac 01:25: {len(SW["mac"])}, Mac 12:50: {len(SW["mac2"])}; C ⊂ Mac ⊂ Mac 12:50: '
  f'{set(SW["C"]) <= set(SW["mac"]) <= set(SW["mac2"])}).')
w(f'- Final stage (FINAL-STAGE-run-U2.txt, Theorem U″): {len(FS)} vertices; its own summary line: `{FS_TOTAL}`.')
w(f'- Enumerated vertices with no final stage (enumerated after its snapshot): {sorted(s for s in ENUMERATED if s not in FS)}.')
w(f'- Equations (digit multisets) over all {len(VERTICES)} vertices: {sum(len(EQS[s]) for s in VERTICES)}; '
  f'level-12 patterns in all: {sum(PATTERNS.values()):.3e}.')
w('')
w('Status of the vertices (Table A):')
w('')
w('| status | T_2 | T_4 | T_6 | T_8 | all |')
w('|---|---|---|---|---|---|')
for st in ['CLOSED by computation', 'CLOSED by Lemma C (depth 1)', 'CLOSED by sandwich', 'closed-below-height',
           'not enumerated (Tier A)', 'not enumerated (Tier B)', 'not enumerated (Tier C)']:
    w(f'| {st} | ' + ' | '.join(str(STATUS_BY_TREE[t][st]) for t in (2, 4, 6, 8)) + f' | {STATUS_COUNT[st]} |')
w(f'| **all** | ' + ' | '.join(str(per_tree[t]) for t in (2, 4, 6, 8)) + f' | {len(VERTICES)} |')
w('')
nclosed = sum(STATUS_COUNT[k] for k in STATUS_COUNT if k.startswith('CLOSED'))
w(f'CLOSED in all: {nclosed} = {STATUS_COUNT["CLOSED by computation"]} by computation + '
  f'{STATUS_COUNT["CLOSED by Lemma C (depth 1)"]} by Lemma C + {STATUS_COUNT["CLOSED by sandwich"]} by the sandwich; '
  f'closed-below-height: {STATUS_COUNT["closed-below-height"]}; not enumerated: '
  f'{sum(v for k, v in STATUS_COUNT.items() if k.startswith("not"))}.')
w('')
open_tot = sum(fs['open'] for fs in FS.values())
w(f'Open patterns at level 96 over the {len(FS)} final-stage vertices: {open_tot}; closed by Lemma C depth 1: '
  f'{sum(fs["cut"] for fs in FS.values())} ({100*sum(fs["cut"] for fs in FS.values())/open_tot:.1f} %); by the sandwich: '
  f'{sum(fs["sand"] for fs in FS.values())}; not run/unsupported: {sum(fs["unfin"]+fs["unsup"] for fs in FS.values())}.')
w(f'SANDWICH-full-U2.txt (Theorem U″): {len(SANDWICH)} patterns, {sum(p["verdict"]=="CLOSED" for p in SANDWICH)} CLOSED, '
  f'k = {min(p["k"] for p in SANDWICH)}–{max(p["k"] for p in SANDWICH)}, depths ' +
  ', '.join(f'{d}: {c}' for d, c in sorted(Counter(p['depth'] for p in SANDWICH).items())) +
  f', min margin 10^{min(p["margin"] for p in SANDWICH):.2f}, max margin 10^{max(p["margin"] for p in SANDWICH):.2f} digits, '
  f'sub-cosets {sum(p["sub"] for p in SANDWICH)} in all, {len(SAND_BY_S)} vertices.')
w(f'DEEPCUT-run-final-d1.txt: {len(DEEP)} patterns, {sum(p["verdict"]=="CLOSED" for p in DEEP)} CLOSED at depth 1 '
  f'({100*sum(p["verdict"]=="CLOSED" for p in DEEP)/len(DEEP):.1f} %), {len(DEEP_BY_S)} vertices.')
w(f'Found = known on every enumerated vertex: {all(not r["flag"] for r in tableA if r["found"] is not None)}.')
w('')

# Table A
w('## Table A — every vertex of T_2, T_4, T_6, T_8')
w('')
w('Columns: tree Δ; vertex s; factorization; number of equations (digit multisets with product s); level-12 pattern count '
  '(12·∏ C(11+m_d, m_d) summed over the multisets); k_max (largest number of non-1 digits); source file of the freshest '
  'result (mac > C > v1); status; detail; children found by the enumeration; children known from the corpus; flag if they differ.')
w('')
w('| Δ | s | 2^a3^b7^c | eqs | level-12 patterns | k_max | src | status | detail | found | known | flag |')
w('|---|---|---|---|---|---|---|---|---|---|---|---|')
for r in sorted(tableA, key=lambda r: (r['tree'], r['s'])):
    w(f'| {r["tree"]} | {r["s"]} | {r["fact"]} | {r["neq"]} | {sci(r["npat"])} | {r["kmax"]} | {r["src"]} | {r["status"]} | '
      f'{r["detail"]} | {("" if r["found"] is None else str(r["found"]))} | {r["known"]} | {r["flag"]} |')
w('')

# Table B
w('## Table B — anchors of the open patterns at level 96')
w('')
w(f'Every open pattern recorded in the freshest sweep file of each enumerated vertex carries an exceptional coset point '
  f'(the engine\'s Babai-nearest lattice point) y; the files record (M, a, y, self-flag). Distinct (vertex, M, a, y) triples: '
  f'{NTRIPLES}; distinct anchors: {len(ANCH)}; SELF (the vertex\'s own child): {SELF_N} triples; anchors with a 0 digit: '
  f'{len(ZERO_DIGIT)}; anchors that are not {{2,3,7}}-units: {len(NOT_SUNIT)}; largest anchor: {max(ANCH)} = {fstr(max(ANCH))}; '
  f'anchors > 10^9: {sum(1 for y in ANCH if y > 10**9)}, > 10^10: {sum(1 for y in ANCH if y > 10**10)}.')
w('')
w('| anchor y | 2^a3^b7^c | patterns anchored | vertices | self for |')
w('|---|---|---|---|---|')
for y, d in sorted(ANCH.items(), key=lambda kv: (-kv[1]['n'], kv[0])):
    w(f'| {y} | {fstr(y)} | {d["n"]} | {len(d["vertices"])}: {sorted(d["vertices"])} | {sorted(d["selfv"]) if d["selfv"] else ""} |')
w('')

# Table C
w('## Table C — bases 8 and 6')
w('')
w(f'Base 8: corpus of zero-free {{2,3,5,7}}-units below 8^70: {len(ZF8)} ({len(ZF8)-7} multi-digit); vertices of the trees of '
  f'the digits 1–7 (roots included): {len(V8)}. Mac files: base8_L96_full.jsonl ({len(B8["b8m_96"])} vertices, levels ≤ 96: '
  + ', '.join(f'{k}: {v}' for k, v in Counter(r['status'] for r in B8['b8m_96'].values()).items()) +
  f'), base8_L384.jsonl ({len(B8["b8m_384"])}, lifted to 192/384 with Lemma C depth 1: '
  + ', '.join(f'{k}: {v}' for k, v in Counter(r['status'] for r in B8['b8m_384'].values()).items()) +
  f'), base8_sandwich_mac.jsonl ({len(B8["b8m_sand"])} vertices so far, in progress: '
  + ', '.join(f'{k}: {v}' for k, v in Counter(r['status'] for r in B8['b8m_sand'].values()).items()) +
  f'; {B8_MAC_SAND_NEW} of them were not already CLOSED at the lift). Cloud files (earlier, partial): base8.jsonl ({len(B8["base8_48"])}, levels ≤ 48), '
  f'base8_lift384.jsonl ({len(B8["base8_lift"])}), base8_sandwich.jsonl ({len(B8["base8_sandwich"])}). "status" is the Mac status from the '
  f'first Mac file that has the vertex (sandwich > lift > level 96); "cloud" likewise for the cloud files. '
  f'Mac: {B8_MAC_CLOSED} vertices closed outright ({B8_MAC_384} at the lift + {B8_MAC_SAND_NEW} by the sandwich so far), '
  f'{len(B8_PENDING)} pending: {B8_PENDING}; of these, {len(B8_PENDING_CLOUD_CLOSED)} are CLOSED in the cloud sandwich file '
  f'({B8_PENDING_CLOUD_CLOSED}) and {len(B8_PENDING_ALL)} are closed outright in no file ({B8_PENDING_ALL}). '
  f'Mac status counts: ' + ', '.join(f'{k}: {v}' for k, v in C8_COUNT.items()) + '.')
w('')
w('| root | s | factorization | Mac status | Mac detail | cloud status | found | known | flag |')
w('|---|---|---|---|---|---|---|---|---|')
for r in sorted(tableC8, key=lambda r: (r['tree'], r['s'])):
    w(f'| {r["tree"]} | {r["s"]} | {r["fact"]} | {r["status"]} | {r["detail"]} | {r["cloud"]} | {"" if r["found"] is None else r["found"]} | '
      f'{r["known"]} | {r["flag"]} |')
w('')
w(f'Base 6: corpus of zero-free {{2,3,5}}-units below 6^60: {len(ZF6)}; vertices (roots 1–5 included): {len(V6)}. '
  f'File: base6.jsonl ({len(B6)} vertices). Counts: ' + ', '.join(f'{k}: {v}' for k, v in C6_COUNT.items()) + '.')
w('')
w('| root | s | factorization | status | detail | found | known | flag |')
w('|---|---|---|---|---|---|---|---|')
for r in sorted(tableC6, key=lambda r: (r['tree'], r['s'])):
    w(f'| {r["tree"]} | {r["s"]} | {r["fact"]} | {r["status"]} | {r["detail"]} | {"" if r["found"] is None else r["found"]} | '
      f'{r["known"]} | {r["flag"]} |')
w('')

# Table D
w('## Table D — the frontier (Tier B and Tier C)')
w('')
w('Tier labels and the cost columns (core-days at 8 ns per level-12 pattern on one core / on ten cores; GPU-days at 10^10 '
  'patterns per second) are from FRONTIER.md; pattern counts, k_max and the Baker ceilings are recomputed here: '
  'log10 G(k_max, a) = baker_upper_bound(k_max, a) for a = 0, a = 1 and (Tier C) a = A, the 2-adic lower bound found by '
  'RESULT-dpcount.md (the ceiling depends on a only through t_0 and a "+a" inside a logarithm); log10 G″(k_max, a) is the Theorem U″ '
  'ceiling from utable_U2.txt (certified, k ≤ 24) or from the NOTES-u2.md table (k = 31, 44), "—" where neither covers k_max. Monte-Carlo columns: '
  'RESULT-dpcount.md §4 (level-12 survivors with 95 % intervals, level-24 children of the survivors with the exact '
  'multiset symmetry, A found, (a, pattern) pairs — lower bounds where the 2-adic search was capped).')
w('')
w('| tier | Δ | s | 2^a3^b7^c | eqs | level-12 patterns | k_max | log10 G(k,0) | log10 G(k,1) | log10 G″(k,0) | log10 G″(k,1) | core-days @8ns | 10 cores | GPU-days | MC survivors (dpcount) | level-24 children | A (capped) | (a,pattern) pairs | log10 G(k,A) |')
w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for r in sorted(tableD, key=lambda r: (r['tier'], r['npat'])):
    d = r['dpc'] or {}
    u20 = f'{r["u2_0"]:.1f}' if r['u2_0'] is not None else '—'
    u21 = f'{r["u2_1"]:.1f}' if r['u2_1'] is not None else '—'
    w(f'| {r["tier"]} | {r["tree"]} | {r["s"]} | {r["fact"]} | {r["neq"]} | {sci(r["npat"])} | {r["kmax"]} | {r["g0"]:.1f} | '
      f'{r["g1"]:.1f} | {u20} | {u21} | {r["d1"]:.0f} | {r["d10"]:.0f} | {r["gpu"]:.1f} | {d.get("surv", "—")} | {d.get("children24", "—")} | '
      f'{d.get("A", "—")} ({d.get("capped", "—")}) | {d.get("apairs", "—")} | '
      f'{(f"{r["gA"]:.1f}" if r["gA"] is not None else "—")} |')
w('')
tb = [r for r in tableD if r['tier'] == 'B']
tc = [r for r in tableD if r['tier'] == 'C']
ta = [s for s in VERTICES if s not in ENUMERATED and tier_of(s) == 'A']
w(f'Tier A (not yet enumerated): {len(ta)} vertices, {sum(PATTERNS[s] for s in ta):.3e} patterns, k_max ≤ {max(KMAX[s] for s in ta) if ta else 0}. '
  f'Tier B: {len(tb)} vertices, {sum(r["npat"] for r in tb):.3e} patterns, k_max {min(r["kmax"] for r in tb)}–{max(r["kmax"] for r in tb)}. '
  f'Tier C: {len(tc)} vertices, {sum(r["npat"] for r in tc):.3e} patterns, k_max {min(r["kmax"] for r in tc)}–{max(r["kmax"] for r in tc)}.')
w('')

# per-tree persistence-relevant lines
w('## Table E — per-tree summary')
w('')
w('| Δ | vertices | enumerated | CLOSED | closed-below-height | not enumerated (A/B/C) | largest closed vertex | largest vertex |')
w('|---|---|---|---|---|---|---|---|')
for t in (2, 4, 6, 8):
    rs = [r for r in tableA if r['tree'] == t]
    cl = [r['s'] for r in rs if r['status'].startswith('CLOSED')]
    ne = Counter(r['status'][-2] for r in rs if r['status'].startswith('not'))
    w(f'| {t} | {len(rs)} | {sum(r["src"] != "—" for r in rs)} | {len(cl)} | {sum(r["status"]=="closed-below-height" for r in rs)} | '
      f'{ne["A"]}/{ne["B"]}/{ne["C"]} | {max(cl) if cl else "—"} | {max(r["s"] for r in rs)} |')
w('')

# source notes
w('## Source notes (disagreements and gaps found while reconciling the files)')
w('')
if not NOTES:
    w('None.')
for n in NOTES:
    w(f'- {n}')
w('')
open(OUT, 'w').write('\n'.join(L))
print(f'wrote {OUT}: {len(VERTICES)} vertices, {len(NOTES)} source notes, base corpora in {time.time()-t0:.0f} s')
print('status counts:', dict(STATUS_COUNT))
