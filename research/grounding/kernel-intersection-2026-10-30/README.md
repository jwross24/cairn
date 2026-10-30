# Which invalid proofs pass both pinned kernels

Executed 2026-10-30 for `cairn-p76j` AC 1. A proof reaches `PROVEN` only through the gold arm, whose comparator runs
pinned nanoda and then the pinned official kernel. So the question that decides exposure is the intersection: which
invalid proofs pass BOTH.

## Result

**0 of 82 invalid proofs pass both pinned kernels.** The two failure sets are disjoint, and each kernel on its own
accepts proofs of `False`.

| Kernel | Accepts of 82 invalid | Valid controls |
|---|---|---|
| official `v4.34.0-rc1` (pinned) | **6** | all accepted |
| nanoda `3a24072` (pinned) | **4** | accepted, except refusals in the table below |
| official `v4.34.1` | 0 | all accepted |
| official `v4.35.0` | 0 | all accepted |
| nanoda `8de7e0c` (HEAD, 2026-10-29) | 1, not a proof of `False` | same refusals as the pin |

The 82 are 33 arena tests with `outcome: reject`, 47 arena `tutorial` tests in `bad/`, and 2 Lean regression tests.

rc1 accepts six proofs of `False`, and `leanchecker --fresh`, the gold arm's replay command, exits 0 on the five it can
read: `bugs/proj-of-stuck-prop`, `bugs/proj-of-subst-prop`, `bugs/rec-of-subst-prop`, `pr14807`
(`kernel_soundness_target`, `axioms=[]`) and `pr14806_2` (`inconsistent`). The sixth, `bugs/rec-missing-ih`, is `.ndjson`
and has no `leanchecker` route on rc1. Pinned nanoda
refuses all six: `expected a sort` or `ensur_sort could not produce a sort` on five, an inductive validity assertion on
`rec-missing-ih`.

Pinned nanoda accepts: `bugs/forged-quot-ind`, `bugs/nested-name-capture`, `bugs/nested-rec-rule-nfields`,
`other/inductive-undeclared-universe`. rc1 rejects all four with a kernel error. The first three are proofs of `False`
and nanoda HEAD refuses them. The fourth is not a proof of `False`, is open as `nanoda_lib#79`, and HEAD still accepts it.

**So each pinned kernel is the only barrier against the other's bugs.** The gate holds by intersection alone.

## How refusals are counted

Rows are not all kernel verdicts, and the runner keeps them apart:

| Outcome | Count | Reading |
|---|---|---|
| rc1 `PARSE-FAIL` on invalid | 6 | `132`, `133`, `134`, `135`, `138`, `139`: duplicate declarations, refused by the pinned parser the comparator also uses |
| nanoda allow-list on invalid | 5 | `011`, `047`, `050`, `053`, `057`: the test's own axioms; rc1 gave a kernel rejection on all five |
| nanoda allow-list on valid | 6 | `init`, `init-prelude`, `std`, `034`, `035`, `107`: gate config refusing `sorryAx`, `Lean.trustCompiler` or test axioms, as designed |
| nanoda `Declined` on valid | 2 | `other/level-index-out-of-order`, `other/sparse-name-index`: nanoda requires contiguous indices, which `lean4export` always writes |

The 31 nanoda refusals outside the tutorial are all typechecker panics, none a decline or an allow-list hit. Panic is
nanoda's rejection path, and the comparator treats any nonzero exit as rejection (`if ret != 0`).

## What was not established

- **Kernel level only.** These runs exercise the two kernels on the comparator's code path. They do not run the full
  gold arm: no Challenge, no `compareAt`, no `checkAxioms`. Nothing here shows a full-gate pass, and with an empty
  intersection none was attempted.
- **Absence of a known exploit is not soundness.** Zero of 82 bounds these 82. Pinned nanoda is 33 commits behind HEAD,
  and both pinned kernels carry bugs fixed upstream.
- **Runtime exploits not run.** #14838 (refcount overflow, `tests/elab/14383.lean`) needs depth 30 and about 12 GB free.
  Whether #14833's GMP 6.1.2 is in the rc1 release is unverified: a string search of `bin/lean` and
  `lib/lean/libleanshared.so` found nothing, and `libleanshared_1.so` and `_2.so` were not searched. `ldd` shows
  `nanoda_bin` links only libgcc_s and libc, so it shares no path with either; that nanoda refuses them is documented in
  the postmortem, not reproduced here.
- **No test for #14843.** #14582's test holds no proof of `False` and was not run; `corner-cases/nested-nonuniform-param`
  is that shape, passes both kernels, and is `either` because the arena knows no `False` from it. `v4.34.1` and `v4.35.0`
  reject it.
- **Not selected:** 28 `perf` accept tests, and the `url:` accept projects `cedar`, `con-leche`, `cslib`, `mathlib`,
  `navier-stokes-euler` and `reachability`. Both `corner-cases/eta-struct-major*-no-whnf` tests time out on every kernel.
- **Candidate runs used rc1 exports**, replayed from an empty environment, on the unmodified driver. They are evidence
  about the kernels, not a build of cairn on those toolchains. Candidate comparisons skip exports over 50 MB (`init`,
  `std`). Candidate nanoda ran natively on macOS; the native pinned build matched the image's accept or refuse verdict on
  all 68 rows compared.

## Environment

- Image `cairn-gate:d6117a22be6f9e25`, the tag the current pins compute to; Lean commit `3447a668`,
  `NANODA_COMMIT=3a2407216ee84a75f9e1aead6803d0578be06ae7`, comparator `575674928e23`, `lean4export` `b18d673`.
- Run with `--network none`, arena tests mounted read-only, because `.lean` tests execute code during elaboration.
- `lean-kernel-arena` at `7e8cc90a3bc1ca827f616d038df13592020c6bf0`.
- `driver/Main.lean` is `runBuiltinKernel` from the comparator, including the Quot post-check, with parse failure given
  its own exit code. nanoda runs under the config the comparator writes.

## Reproducing

`H` is a directory mounted as `/work`, holding `driver/`, `tut/` and `pr/`. Lean regression tests are fetched at their
merge commits into `pr/`: `tests/elab/kernel_is_prop_ensure_sort.lean` at `7412bc4c`,
`tests/elab/kernel_is_def_eq_equiv_manager_2.lean` at `d108aae3`.

```bash
docker run -d --name p76j-probe --network none --entrypoint sleep -v "$H":/work -v "$ARENA/tests":/arena:ro cairn-gate:d6117a22be6f9e25 86400
docker exec p76j-probe sh -c 'cd /work/driver && lake build probe'
uv run --no-project --with pyyaml python runner.py "$ARENA" "$H" all
uv run --no-project python pr_runner.py "$H"
uv run --no-project python dir_runner.py "$H"
docker exec p76j-probe sh -c 'cd /work/tut && OUT=/work/out/tutorial LEAN_ABORT_ON_PANIC=1 lake env lean Tutorial.lean'
uv run --no-project python tutorial_run.py "$H"
uv run --no-project python official_compare.py "$H" "$ARENA/tests"
uv run --no-project python nanoda_compare.py "$H" "$ARENA/tests"
```

`tut/` is the arena's `tutorial/` with `lakefile.toml` here: the git dependency is replaced by a path dependency on the
image's `lean4export`, and `lake update` writes the manifest offline. `runner.py` prints `NO-ROUTE`, `NO-OUTCOME` and
`NOT-SELECTED` for every test it does not run.

Verdicts are in `results/`. `export_sha256` pins the bytes each row checked. `tutorial_results.json` is the verdict table;
`tutorial_results.full.json.gz` is the same rows with nanoda's verbatim output, whose identifiers codespell reads as typos.
