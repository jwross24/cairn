import os, sys, json, time, shutil, subprocess
from gv_lib import *

NEGATIVES = [
    dict(name='neg_lvl12_dlog_table_entry', target='lvl12', find='read_cfg(argv[1]);',
         replace='read_cfg(argv[1]); LOGT[2][5]=(LOGT[2][5]+1)%(int)(P[2]-1);', expect='kill', source='planted negative: one discrete-log table entry changed'),
    dict(name='neg_lvlN_dlog_table_entry', target='lvlN', find='read_cfg(argv[1]);',
         replace='read_cfg(argv[1]); for(int i_=0;i_<np;i_++) if(LOGT[i_]) LOGT[i_][2]=(LOGT[i_][2]+1)%(int)(P[i_]-1);', expect='kill', source='planted negative: one discrete-log table entry changed'),
]


def apply_mutant(src_text, m):
    n = src_text.count(m['find'])
    if n != 1:
        return None, f"find-string occurs {n} times"
    return src_text.replace(m['find'], m['replace']), None


def source_for(target, args, cand):
    given = getattr(args, 'lvl12_src' if target == 'lvl12' else 'lvlN_src', None)
    if given:
        return os.path.abspath(given)
    for c in (os.path.join(os.path.dirname(cand), target + '.c'), cand + '.c'):
        if os.path.exists(c):
            return c
    return None


def run_mutants(ctx, mutants, cand12, candN, src12, srcN, fh, cc=None, label='mutants'):
    from gatev2 import run_gate, log
    work = ctx['work']
    rows = []
    for m in mutants:
        t0 = time.time()
        tgt = m['target']
        cand, src = (cand12, src12) if tgt == 'lvl12' else (candN, srcN)
        row = dict(name=m['name'], target=tgt, expect=m.get('expect', 'kill'))
        if not cand or not src:
            row.update(verdict='SKIP', how=f'no {tgt} candidate/source supplied')
            rows.append(row)
            continue
        text, err = apply_mutant(open(src).read(), m)
        if text is None:
            row.update(verdict='INAPPLICABLE', how=err)
            rows.append(row)
            continue
        d = os.path.join(work, 'mut', m['name'])
        os.makedirs(d, exist_ok=True)
        cp = os.path.join(d, tgt + '.c')
        open(cp, 'w').write(text)
        bp = os.path.join(d, tgt)
        rc, blog = build(cp, bp, cc.split() if cc else None)
        if rc:
            row.update(verdict='BUILD-FAIL', how=blog.strip()[:160])
            rows.append(row)
            continue
        st = run_gate(ctx, bp if tgt == 'lvl12' else None, bp if tgt == 'lvlN' else None, early=True, big=False, vertices=False)
        fl = [(s['name'], f) for k, s in st.items() if isinstance(s, dict) and 'findings' in s for f in s['findings']]
        if fl:
            stage, f = fl[0]
            row.update(verdict='KILLED', how=f"{stage.split(' (')[0]} / {f['kind']}: {f['text'].splitlines()[0][:110]}")
        else:
            row.update(verdict='SURVIVED', how='no difference in any stage')
        row['secs'] = round(time.time() - t0, 1)
        log(f"mutant {m['name']}: {row['verdict']} ({row['secs']}s) {row['how'][:90]}", fh)
        rows.append(row)
    return rows


def judge(rows):
    bad = []
    for r in rows:
        exp = r['expect']
        if r['verdict'] in ('INAPPLICABLE', 'BUILD-FAIL'):
            bad.append(r)
        elif r['verdict'] == 'SURVIVED' and exp == 'kill':
            bad.append(r)
        elif r['verdict'] == 'KILLED' and exp.startswith('equivalent'):
            pass
    return bad


def fmt(rows):
    w = max(len(r['name']) for r in rows)
    out = []
    for r in rows:
        tag = r['verdict']
        if r['verdict'] == 'SURVIVED' and r['expect'].startswith('equivalent'):
            tag = f"SURVIVED ({r['expect']}, expected)"
        out.append(f"  {r['name'].ljust(w)} {r['target']:<5} {tag:<34} {r.get('how', '')[:100]}")
    return '\n'.join(out)


def mutant_stage(ctx, args, cand12, candN, fh):
    from gatev2 import log
    mutants = json.load(open(args.mutants))
    src12 = source_for('lvl12', args, cand12) if cand12 else None
    srcN = source_for('lvlN', args, candN) if candN else None
    rows = run_mutants(ctx, mutants, cand12, candN, src12, srcN, fh, args.cc)
    bad = judge(rows)
    txt = fmt(rows)
    log("mutant table:\n" + txt, fh)
    open(os.path.join(ctx['logdir'], 'mutants.txt'), 'w').write(txt + '\n')
    json.dump(rows, open(os.path.join(ctx['logdir'], 'mutants.json'), 'w'), indent=1)
    k = sum(1 for r in rows if r['verdict'] == 'KILLED')
    sk = sum(1 for r in rows if r['verdict'] == 'SKIP')
    det = f"{k} killed, {sum(1 for r in rows if r['verdict'] == 'SURVIVED')} survived, {sk} skipped of {len(rows)}"
    fl = [dict(kind='mutant', label=r['name'], text=f"{r['verdict']}: {r.get('how', '')}") for r in bad]
    return dict(name='mutation runner', status='FAIL' if bad else 'PASS', detail=det, findings=fl)


def selftest(ctx, fh, args):
    from gatev2 import run_gate, log, table
    refs = ctx['refs']
    ok = True
    log("SELFTEST 1/3: reference vs reference must PASS", fh)
    st = run_gate(ctx, refs['lvl12'], refs['lvlN'], big=not ctx.get('quick'))
    tab = table({k: v for k, v in st.items() if isinstance(v, dict) and 'status' in v})
    log("\n" + tab, fh)
    bad = [k for k, v in st.items() if isinstance(v, dict) and v.get('status') == 'FAIL']
    log(f"SELFTEST 1/3: {'PASS' if not bad else 'FAIL ' + str(bad)}", fh)
    ok &= not bad
    log("SELFTEST 2/3: planted negatives (one dlog table entry changed) must FAIL item 1 or 3", fh)
    rows = run_mutants(ctx, NEGATIVES, refs['lvl12'], refs['lvlN'], os.path.join(ctx['work'], 'ref', 'lvl12.c'), os.path.join(ctx['work'], 'ref', 'lvlN.c'), fh, args.cc)
    log(fmt(rows), fh)
    n_ok = all(r['verdict'] == 'KILLED' for r in rows)
    log(f"SELFTEST 2/3: {'PASS' if n_ok else 'FAIL'}", fh)
    ok &= n_ok
    log("SELFTEST 3/3: MUTATION-opt.md seeds against tier0-opt/lvl12.c and the reference lvlN.c", fh)
    seeds = json.load(open(os.path.join(HERE, 'mutants_seed.json')))
    opt = os.path.join(PERSIST, 'tier0-opt', 'lvl12.c')
    ob = os.path.join(ctx['work'], 'cand', 'opt_lvl12')
    os.makedirs(os.path.dirname(ob), exist_ok=True)
    rc, blog = build(opt, ob)
    if rc:
        raise SystemExit(blog)
    rows = run_mutants(ctx, seeds, ob, refs['lvlN'], opt, os.path.join(ctx['work'], 'ref', 'lvlN.c'), fh, args.cc)
    txt = fmt(rows)
    log("mutant table:\n" + txt, fh)
    open(os.path.join(ctx['logdir'], 'mutants.txt'), 'w').write(txt + '\n')
    bad = judge(rows)
    log(f"SELFTEST 3/3: {'PASS' if not bad else 'FAIL ' + str([r['name'] for r in bad])}", fh)
    ok &= not bad
    log(f"SELFTEST: {'PASS' if ok else 'FAIL'}", fh)
    return ok
