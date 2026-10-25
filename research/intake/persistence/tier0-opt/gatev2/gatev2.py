#!/usr/bin/env python3
"""gate v2: shared verification harness for optimized lvl12 / lvlN persistence kernels.

  gatev2 --lvl12 <bin> [--lvlN <bin>] [--fast | --quick] [--mutants mutants_seed.json --lvl12-src lvl12.c --lvlN-src lvlN.c]
  gatev2 --selftest          reference vs reference PASS, planted negatives FAIL, seed mutants KILLED
  gatev2 --coverage-only     branch coverage of the frozen reference kernels

Reference kernels: tier0-opt/reference/{lvl12,lvlN}.c (md5 pinned), built into <work>/ref. Python support: tier0/*.py, copied to <work>/src.
Work dir default /private/tmp/persist-gatev2/work; reference results are cached there, so a second candidate pays only its own cost.

Measured run time, --jobs 3 (nice 10), optimized lvl12 candidate:
  --fast    103 equations, 21 cheapest plants, 72/224 pipelines, no coverage          30 s warm cache, 45 s cold
  --quick   520 equations + 331 genuine parents + 39 plants + vertices + coverage     about 3 min (coverage is 2.5 min; --no-coverage drops it)
  default   --quick plus level 12 of every multiset of 10800 and 14336 (3.6e9 patterns) 3 min 41 s warm; the first run also computes the reference side of those (about 4 more min)
A candidate as slow as the reference (66 ns/pattern) takes 4.5 min for the differential, vertices and plants of the default run.
Exit status 0 only if no stage is FAIL. A stage REFUSES (candidate exits loudly on an off-nominal config) is reported and does not fail the gate.
"""
import os, sys, json, time, argparse, datetime, traceback, shutil, multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gv_lib import *
import gv_corpus as C
import gv_stages as S


def log(msg, fh=None):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + '\n')
        fh.flush()


FIXED_BIG = (10800, 14336)
FIXED_FULL = (72, 224)


def fixed_eqs():
    out = []
    for s in FIXED_FULL:
        for M in sorted(C.multisets(s)):
            out.append(dict(id=f'f{len(out):03d}', s=s, M=list(M), tag=f'v{s}', npat=C.npat(M)))
    return out


def big_jobs(ctx, cand12):
    jobs = []
    for s in FIXED_BIG:
        for M in sorted(C.multisets(s), key=C.npat):
            jobs.append(dict(work=ctx['work'], s=s, M=list(M), npat=C.npat(M), ref12=ctx['refs']['lvl12'], cand12=cand12, logdir=ctx['logdir']))
    return jobs


def stage_result(name, findings, detail, status=None):
    return dict(name=name, status=status or ('FAIL' if findings else 'PASS'), detail=detail, findings=findings)


def run_gate(ctx, cand12, candN, early=False, plants=True, big=True, vertices=True, label=''):
    pool, work, refs = ctx['pool'], ctx['work'], ctx['refs']
    st = {}
    t0 = time.time()
    eqs = ctx['corpus']
    base = dict(work=work, ref12=refs['lvl12'], refN=refs['lvlN'], cand12=cand12, candN=candN, logdir=ctx['logdir'])
    jobs = [dict(base, eq=e) for e in sorted(eqs, key=lambda e: e['npat'])]
    jobs += [dict(base, eq=e, max_parents=100000, max_children=5_000_000, split_all=True) for e in fixed_eqs()]
    nvol = 1 if ctx.get('fast') else 4
    vols = sorted(eqs, key=lambda e: -e['npat'])[:nvol]
    jobs += [dict(base, eq=dict(e, id=f"v{i:03d}"), max_parents=200000, max_children=6_000_000) for i, e in enumerate(vols)]
    killed = None
    results = []
    futs = [pool.submit(S.eq_task, j) for j in jobs]
    bigf = [pool.submit(S.big_task, j) for j in big_jobs(ctx, cand12)] if (big and cand12 and not early) else []
    for f in as_completed(futs):
        try:
            r = f.result()
        except BaseException as e:
            r = dict(id='?', findings=[dict(kind='crash', label='worker', text=''.join(traceback.format_exception_only(type(e), e)))], stats={}, inputs=[])
        results.append(r)
        if early and any(x['kind'] != 'refrc' for x in r['findings']):
            for g in futs:
                g.cancel()
            break
    allf = [x for r in results for x in r['findings']]
    isN = lambda x: '_chain' in x['label'] or '_wild' in x['label']
    f12 = [x for x in allf if not isN(x)]
    fN = [x for x in allf if isN(x)]
    refbad = [x for x in fN + f12 if x['kind'] == 'refrc']
    n_done = len(results)
    st['corpus12'] = stage_result('lvl12 differential (corpus + 72/224)', f12 if cand12 else [], f"{n_done} equations, raw sorted stdout + stderr counters", None if cand12 else 'SKIP')
    st['corpusN'] = stage_result('lvlN differential (corpus + 72/224)', fN if candN else [], f"{n_done} equations, parents from reference chain + wild parents; raw sorted stdout, counters, python-side reconstruction", None if candN else 'SKIP')
    bigres = []
    if bigf:
        for f in as_completed(bigf):
            bigres.append(f.result())
        bf = [x for r in bigres for x in r['findings']]
        tot = sum(r['npat'] for r in bigres)
        st['big'] = stage_result('lvl12 full vertices 10800, 14336', bf, f"{len(bigres)} multisets, {tot:.3e} patterns, level 12 only (lifts for these two vertices not run)")
    if (cand12 or candN) and ctx.get('synth', True) and not early:
        sj = []
        if cand12:
            small = [e for e in eqs if e['npat'] <= 300000]
            bases = [max(small, key=lambda e: e['npat']), max(small, key=lambda e: (C.export12(work, tuple(e['M']))[1]['A'], e['npat']))]
            for e in bases[:1 if ctx.get('fast') else 2]:
                cp, _ = C.export12(work, tuple(e['M']))
                for tag, p in C.synth_cfgs(work, cp):
                    sj.append(pool.submit(S.synth_task, dict(work=work, kernel='lvl12', args=[p], tag=f"{tag}_{e['id']}", ref12=refs['lvl12'], cand12=cand12, logdir=ctx['logdir'])))
        if candN:
            for it in C.synthN_inputs(work, ctx.get('genuine', [])):
                sj.append(pool.submit(S.synth_task, dict(work=work, kernel='lvlN', args=it['args'], tag=it['tag'], refN=refs['lvlN'], candN=candN, logdir=ctx['logdir'])))
        sres = [f.result() for f in sj]
        bad = [r for r in sres if r['verdict'] in ('DIVERGED', 'CRASH')]
        ref_ = [r for r in sres if r['verdict'] == 'REFUSES']
        fl = [dict(kind='offnominal', label=r['tag'], text=f"{r['verdict']}: {r['text']}") for r in bad]
        cnt = {v: sum(1 for r in sres if r['verdict'] == v) for v in ('EQUIVALENT', 'REFUSES', 'DIVERGED', 'CRASH')}
        stt = 'FAIL' if bad else ('REFUSES' if ref_ else 'PASS')
        st['synth'] = stage_result('off-nominal configs (K != 3, np = 7)', fl, f"{len(sres)} configs: {cnt}" + (f"; loud refusals (non-equivalent, reported): {sorted(r['tag'] for r in ref_)}" if ref_ else ''), stt)
        st['_synth'] = sres
    if early and (st['corpus12']['findings'] or st['corpusN']['findings']):
        return st
    gen = ctx.get('genuine', [])
    if gen:
        gj = [pool.submit(S.genuine_task, dict(work=work, g=g, refN=refs['lvlN'], candN=candN, logdir=ctx['logdir'])) for g in gen]
        gres = [f.result() for f in gj]
        st['_genuine'] = gres
        gf = [x for r in gres for x in r['findings']]
        if candN or any(x['kind'] == 'refrc' for x in gf):
            st['corpusN']['findings'] += gf
            if gf:
                st['corpusN']['status'] = 'FAIL'
        st['corpusN']['detail'] += f"; {len(gen)} genuine-parent chains (true child must reappear)"
        results = results + gres
    st['_eq_results'] = results
    st['_big_results'] = bigres
    if early and any(s_['findings'] for k, s_ in st.items() if isinstance(s_, dict) and 'findings' in s_):
        return st
    if vertices:
        pj = []
        for pid, (l12, lN) in (('ref', (refs['lvl12'], refs['lvlN'])), ('cand', (cand12 or refs['lvl12'], candN or refs['lvlN']))):
            pipe = make_pipe(work, f"{pid}_{os.path.basename(os.path.dirname(l12))}_{os.path.basename(l12)}_{md5file(l12)[:8]}_{md5file(lN)[:8]}", l12, lN)
            for s in FIXED_FULL:
                pj.append((pid, s, pool.submit(S.vertex_task, dict(work=work, pipe=pipe, s=s, pipe_id=(md5file(l12) + md5file(lN)), cache=(pid == 'ref')))))
        vres = {(pid, s): f.result() for pid, s, f in pj}
        vf = []
        for s in FIXED_FULL:
            a, b = vres[('ref', s)], vres[('cand', s)]
            if a['rc'] or not a['rows']:
                vf.append(dict(kind='refrc', label=f'vertex{s}', text=f"reference pipeline failed: {a.get('err')}"))
            elif a['rows'] != b['rows'] or b['rc']:
                diffs = [f"ref {x}\n  cand {y}" for x, y in zip(a['rows'], b['rows']) if x != y]
                vf.append(dict(kind='pipeline', label=f'vertex{s}', text=f"run_vertex_c output differs (rc cand {b['rc']}; {len(a['rows'])} vs {len(b['rows'])} rows): " + (diffs[0] if diffs else b.get('err', ''))))
        nrows = sum(len(vres[('ref', s)]['rows']) for s in FIXED_FULL)
        st['vertex'] = stage_result('python pipeline run_vertex_c 72, 224', vf, f"{nrows} rows (open counts, children, per-level survivors, c_stats) ref vs cand")
        st['_vertex'] = {f"{k[0]}{k[1]}": v for k, v in vres.items()}
    if early and any(s_['findings'] for k, s_ in st.items() if isinstance(s_, dict) and 'findings' in s_):
        return st
    if plants:
        pipe = make_pipe(work, f"plant_{md5file(cand12 or refs['lvl12'])[:8]}_{md5file(candN or refs['lvlN'])[:8]}", cand12 or refs['lvl12'], candN or refs['lvlN'])
        pl = ctx['plants']
        pf = [pool.submit(S.plant_task, dict(work=work, pipe=pipe, plant=p)) for p in pl]
        pres = []
        for f in as_completed(pf):
            r = f.result()
            pres.append(r)
            if early and not r['found']:
                for g in pf:
                    g.cancel()
                break
        lost = [r for r in pres if not r['found']]
        fl = [dict(kind='plant', label=f"plant{r['plant']['y']}", text=f"planted child {r['plant']['y']} (M={r['plant']['M']}, {r['plant']['n']} digits) NOT recovered: {r.get('lost') or 'absent from solutions'}") for r in lost]
        found = sum(1 for r in pres if r['found'])
        st['plants'] = stage_result('planted children (pipeline)', fl, f"{found}/{len(pres)} recovered")
        st['_plants'] = pres
    st['_secs'] = time.time() - t0
    return st


def table(stages):
    rows = [(s['name'], s['status'], s['detail']) for k, s in stages.items() if isinstance(s, dict) and 'status' in s]
    w = max(len(r[0]) for r in rows)
    lines = [f"{'STAGE'.ljust(w)}  VERDICT  DETAIL", '-' * (w + 40)]
    for n, v, d in rows:
        lines.append(f"{n.ljust(w)}  {v:<7}  {d}")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lvl12')
    ap.add_argument('--lvlN')
    ap.add_argument('--mutants', help='mutant list (JSON); see mutants_seed.json')
    ap.add_argument('--lvl12-src')
    ap.add_argument('--lvlN-src')
    ap.add_argument('--work', default=DEFAULT_WORK)
    ap.add_argument('--out', help='log directory (default: gatev2/logs/<timestamp>)')
    ap.add_argument('--jobs', type=int, default=3, help='worker processes (max 4)')
    ap.add_argument('--no-coverage', action='store_true')
    ap.add_argument('--coverage-only', action='store_true')
    ap.add_argument('--heavy', action='store_true', help='add the 13-digit plant (5.9e8 patterns)')
    ap.add_argument('--selftest', action='store_true', help='reference vs reference must PASS; broken candidates must FAIL')
    ap.add_argument('--mutants-only', action='store_true')
    ap.add_argument('--quick', action='store_true', help='full corpus and plants, skip the 10800/14336 level-12 runs (about 5-7 min with an optimized lvl12)')
    ap.add_argument('--fast', action='store_true', help='~110-equation subset, 21 cheapest plants, 72/224 pipelines, one off-nominal base (about 2-4 min)')
    ap.add_argument('--cc', default=None, help='compiler command for mutant builds (default: cc -O3 -march=native)')
    a = ap.parse_args()
    try:
        os.nice(10)
    except OSError:
        pass
    jobs = max(1, min(4, a.jobs))
    out = a.out or os.path.join(HERE, 'logs', time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(out, exist_ok=True)
    fh = open(os.path.join(out, 'gatev2.log'), 'w')
    refs = setup_work(a.work)
    C.init_py(a.work)
    corpus = C.build_corpus()
    plants = C.plants(heavy=a.heavy)
    if a.fast:
        corpus = C.fast_subset(corpus)
        plants = C.fast_plants(plants)
        a.quick = True
        a.no_coverage = True
    json.dump(dict(corpus=corpus, plants=plants), open(os.path.join(out, 'corpus.json'), 'w'))
    log(f"gate v2: {len(corpus)} equations, {len(plants)} plants, jobs={jobs}, logs {out}", fh)
    gen = {r['y']: r for r in C.small_units(4 if a.fast else 6)}
    for p in plants:
        gen[p['y']] = p
    ctx = dict(genuine=sorted(gen.values(), key=lambda r: r['y']), work=a.work, refs=refs, logdir=out, corpus=corpus, plants=plants, quick=a.quick, fast=a.fast, jobs=jobs)
    cand12 = os.path.abspath(a.lvl12) if a.lvl12 else None
    candN = os.path.abspath(a.lvlN) if a.lvlN else None
    final = {}
    ok = True
    with ProcessPoolExecutor(max_workers=jobs, mp_context=mp.get_context('spawn')) as pool:
        ctx['pool'] = pool
        if a.selftest:
            import gv_mutate as MU
            ok = MU.selftest(ctx, fh, a)
            return 0 if ok else 1
        stages = {}
        if (cand12 or candN) and not a.mutants_only and not a.coverage_only:
            for p, nm in ((cand12, 'lvl12'), (candN, 'lvlN')):
                if p and not os.path.exists(p):
                    raise SystemExit(f"{nm} binary not found: {p}")
            if a.quick:
                global FIXED_BIG
                FIXED_BIG = ()
            t0 = time.time()
            log(f"candidate lvl12={cand12} lvlN={candN}", fh)
            stages = run_gate(ctx, cand12, candN, big=not a.quick)
            log(f"differential + plants done in {time.time() - t0:.0f}s", fh)
            json.dump({k: v for k, v in stages.items() if not k.startswith('_') or k in ('_plants', '_vertex')}, open(os.path.join(out, 'stages.json'), 'w'), default=str, indent=1)
            manifest = [i for r in stages['_eq_results'] for i in r['inputs']]
            json.dump(manifest, open(os.path.join(a.work, 'manifest.json'), 'w'))
            ctx['eq_results'] = stages['_eq_results']
        if not a.no_coverage:
            import gv_cov as CV
            if 'eq_results' not in ctx:
                mp_ = os.path.join(a.work, 'manifest.json')
                ctx['manifest'] = json.load(open(mp_)) if os.path.exists(mp_) else None
            else:
                ctx['manifest'] = [i for r in ctx['eq_results'] for i in r['inputs']]
            stages['coverage'] = CV.coverage_stage(ctx, fh)
        if a.mutants:
            import gv_mutate as MU
            stages['mutants'] = MU.mutant_stage(ctx, a, cand12, candN, fh)
    for k, s in stages.items():
        if isinstance(s, dict) and 'status' in s:
            for f in s['findings']:
                log(f"FINDING [{s['name']}] {f['kind']} {f['label']}: {f['text']}", fh)
    tab = table(stages)
    log("\n" + tab, fh)
    allpass = all(s['status'] in ('PASS', 'SKIP', 'REFUSES') for s in stages.values() if isinstance(s, dict) and 'status' in s)
    note = ' (on-contract; off-nominal configs REFUSE loudly, see table)' if allpass and any(s.get('status') == 'REFUSES' for s in stages.values() if isinstance(s, dict)) else ''
    log(f"GATE v2: {'PASS' if allpass else 'FAIL'}{note}", fh)
    open(os.path.join(out, 'summary.txt'), 'w').write(tab + f"\nGATE v2: {'PASS' if allpass else 'FAIL'}{note}\n")
    return 0 if allpass else 1


if __name__ == '__main__':
    sys.exit(main())
