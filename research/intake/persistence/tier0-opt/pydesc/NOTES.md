# Python stage of the persistence engine (untracked research code)

Scope: descent, classification and per-equation setup in `tier0/` (`tier0v2.py`, `run_c.py`, `export_level.py`,
`export_cfg.py`). `tier0/` itself was not edited; every run used a scratch copy under `/private/tmp/persist-pydesc/`
with the production binaries (`tier0/lvl12` = lvl12_r2, `tier0/lvlN` = lvln).

## Files

`tier0v2.py`, `run_c.py`, `export_level.py`, `export_cfg.py` replace the same-named files in `tier0/`; `pydesc.py` and
`libpydesc.dylib` are new; `pydesc.c` and `build.sh` build the library (Homebrew GMP linked statically).
`PYDESC=0` selects the original Python path; a missing library raises with a build hint.

## Swap procedure

Base: the candidates derive from exactly these `tier0/` versions (md5 checked at 20:25 EDT, unchanged since the copy):
`tier0v2.py e7ea31d0be1792423569b8cd3b488778`, `run_c.py f4c459b9e028882aeee06d94cd193356`,
`export_level.py 7b5d6d0584e6296eb5c906ef81d5b09d`, `export_cfg.py b423f65fd7ec6b96e8926d92a26f0e83`.
Rerun `md5 -q` on them before swapping; if any differs, rebase the change onto it and rerun `tools/fullgate.sh`.

```
P=/Users/jwross/Documents/cairn/research/intake/persistence
mkdir -p $P/tier0-opt/pydesc/backup-pre-swap
cp -p $P/tier0/tier0v2.py $P/tier0/run_c.py $P/tier0/export_level.py $P/tier0/export_cfg.py $P/tier0-opt/pydesc/backup-pre-swap/
cd $P/tier0-opt/pydesc && sh build.sh                      # rebuilds libpydesc.dylib here (optional; a prebuilt one is shipped)
cp -p tier0v2.py run_c.py export_level.py export_cfg.py pydesc.py libpydesc.dylib $P/tier0/
cd $P/tier0 && uv run --no-project --with gmpy2 --with sympy python -c "import run_c, pydesc; pydesc._load(); print('ok')"
```

`pydesc.py` finds the library next to itself (`tier0/libpydesc.dylib`), and `run_trees_c_v2.py` imports `tier0v2` and
`run_c` from its own directory, so the five Python files and the dylib all belong in `tier0/`. Processes started before
the swap keep the old modules in memory (all imports happen at start); the new code takes effect at the next start of
`run_trees_c_v2.py`, which resumes from its output files. Rollback: copy the four files back from
`backup-pre-swap/` and delete nothing else (`PYDESC=0` also selects the old path while keeping the new files).
`gatev2`'s `setup_work` copies `tier0/*.py` only; add `*.dylib` to that glob (`tools/gatev2_overlay.patch` shows the
scratch version) or its pipelines fail loudly on the missing library.

## Design

`libpydesc` (C, GMP) takes a batch of survivors and returns, per survivor, the result of `classify`, `ten_adic_K` and
`descend` (kind, solutions). It declines (code 9) anything it cannot decide exactly (a size limit, a failed invariant);
the caller then reruns that batch through the original Python code, which also raises whatever the old code raised.
Level-12 survivors are not turned into Python tuples: the library reads the kernel's output files, validates every
line against what the Python parser accepts (a line it would reject sends the whole equation down the original parse),
canonicalizes, classifies, and returns only the OPEN survivors. Kinds come back in first-seen order so `dict(cls)` keeps
its key order.

Caches (all keyed by the level prefix, which determines them): `PrimeData`, `Prefilter`, `FastLevel`, `FastLevelGen`;
the multiset-independent part of each level's config text and JSON; `ten_adic_K` of the fixed lattices;
`two_adic_bound`. Lattice work inside the library is cached per lattice (K per `a`, and the kernel data of every
congruence applied to it), so a cut costs one discrete logarithm and a few multiplications.

## Isomorphism notes

- Decisions depend on a coset only through its lattice, `ten_adic_K` (basis independent) and the tail value at that K
  (representative independent), so the library uses its own exact Lagrange reduction in place of the float `round` in
  `lattice._reduce`.
- Duplicate `(digit, residue)` entries of a pattern produce identical subtrees; the library visits one of them. The
  result is a union / OR over children, and the depth-12 early return depends only on whether some child exists.
- A child's `ten_adic_K` equals the imposed Kp (proved below), so its tail is `Yp`; the library declines otherwise.
- The 5-adic discrete log in `(Z/5^k)^*` returns the canonical representative in `[0, 4*5^(k-1))`.

## Gate record (`logs/`)

Final candidate (c8) and every earlier lever: `difftest.py` on 72, 224, 10800 IDENTICAL; `run_vertex_c` on 14336, 72,
224 (and 131712 at 4 cores) byte-identical to production; `run_trees_c_v2` row for 14336 identical; gatev2 `--fast` PASS.
The final candidate also passes the full gatev2 (default stage with level 12 of 10800 and 14336, coverage on, 4 jobs):
538 equations, 39/39 plants, python pipeline stage PASS (`gate_c8_full_summary.txt`). gatev2's own coverage covers the
frozen reference kernels (lvl12 lines 98.8%, branches 96.6%; lvlN lines 99.3%, branches 93.4%), not `pydesc.c`.

Coverage of the new code (`logs/coverage_*.txt`): `pydesc.c` lines 98.98% (972 of 982), functions 100%, regions 91.5%,
branches 77.75%. Missed lines: the empty-lattice edge case, the error return for a malformed header, and the fallback
handler (executed 19,856 times, but llvm-cov loses counters across `_longjmp`). Python (line+branch): `export_cfg.py` 90%,
`export_level.py` 95%, `pydesc.py` 83%, `run_c.py` 81%, `tier0v2.py` 72% (the rest of `tier0v2.py` is unchanged code).

Library differential (`tools/cmp_c.py`): 945,153 survivors (every classify call of the 14336 and 10800 vertices plus
synthetic cosets), 0 mismatches and 0 fallbacks; restricted `kcap` gives fallbacks only, never a wrong answer.
Planted negatives: a pipeline that drops the solutions fails the gate; 8 of 11 C mutants are killed by mismatches, one by
fallbacks (`m11`); the two guard-weakening mutants (`m12`, `m13`) are equivalent on every input (below).

## Branches no pipeline input reaches (proved, not sampled)

Descent only runs with `K = ten_adic_K(lattice, a) >= 1` (`classify_one`: `K == 0` returns before `descend_core`).

1. A step is attempted only for `e` in `[K, t]` with `t = v2(9Y - 10^K)` (`descend_core`, loop bounds). `K > a` forces
   `v2(Y) = a` and so `t = a`, which returns OPEN before any step. So steps need `K <= a`. For `e <= t`,
   `9*Yp = 9Y - 10^K + (1 + 9d)*10^e` is divisible by `2^e`, hence `v2(Yp) >= e`. `cut_coset` requires `v2(Yp mod 2^Kp)
   = a` when `Kp = e + 1 > a`, which forces `a = e`, i.e. `Kp - a = 1`. The cuts with `Kp - a >= 2` (the former
   `k2 == 2` and `k2 >= 3` stages, `dlog2`, `ensure_l2`) cannot occur. The library no longer contains them: the case
   is a fallback (`if (Kp - a != 1) FAIL();`).
2. For the remaining cuts the 2-adic condition is vacuous, so the child lattice is `{v5(3^b 7^c - 1) >= Kp}`. With
   `K >= 1` every vector has `3^b 7^c = 1 (mod 5)`, hence `b = c (mod 4)` and `3^b 7^c = 1 (mod 4)`, so both valuations
   are logarithmic: `v5(z - 1) = v5(L5)`, `v2(z - 1) >= 2`. The image of Z in Z_5 is dense, so some vector has `v5` exactly
   `Kp` whenever `Kp > m5`. `Kp > K` and `K <= a` force `m5 = K < Kp`, and `a + v2 >= a + 2 >= Kp`. Therefore
   `K2 == Kp`, the child tail is `Yp` (exactly `Kp` digits, top digit `d >= 2`), and a child tail with a leading zero or
   `K2 > Kp` cannot happen. The library enforces it (`if (K2 != Kp) FAIL();`, `if (len != K) FAIL();`). Over 945,153
   survivors the guard never declined, and `tools/k2search.py` found `K2 == Kp` in 30,002 random
   (lattice, a, Kp) triples with `K >= 1` (and violations only with `K = 0`, which never descends).
3. `make_edge` with `A2 = B2 = 0` (all of the lattice already satisfies the congruence) would need `m5 >= Kp > K`,
   contradicting `m5 = K`.

Mutants `m7` (leading-zero child tail) and `m9` (`K2 <= Kp + 1` shortcut) of the previous round targeted code that item 2
removed.

## Memory

Vertex 131712 at 4 cores (`tools/memrun.py`): 15 equations, 21.5 s, peak RSS 282 MB; production 147.8 s, peak RSS
562 MB. RSS after the equations of one vertex: 160 MB after the third, 209 MB after the last (larger equations hold
more survivors). The lattice cache does not grow with equations processed: the same 12 equations run four times in one
process give 168, 170, 171, 171 MB after the passes (`tools/memrepeat.py`). Cache size is bounded at 4e6 lattices and
reset on a `kcap` change (`tools/reset_test.py`).

## Importers of `tier0v2` / `run_c` in `tier0/`

`run_vertex_c.py`, `run_trees_c_v2.py`, `run_trees_c.py`, `run_trees_c_v3.py` (call `run_c.run`; covered by the vertex
and trees comparisons; v1 and v3 share the code path of v2), `runall_v2.py` (calls `solve_equation` without level-12
input, token-batch path: `tools/solve_cmp.py` gives an identical digest for 72 equations over s = 2..224 including open
cosets), `tables.py` and `fastlevel.py`'s self-test (import `multisets` and `PrimeData` only), `difftest.py` (via
`run_vertex_c.py`). `crosscheck.py`, `deepcut*.py`, `sandwich*.py`, `classify_open.py`, `lemma_c_blind.py` import
`tier0`, `descent`, `lattice` or `deepcut` and none of the swapped modules, so the swap cannot change them;
`deepcut.py runall_final.jsonl --depth 1` run from overlays of the current `tier0/` with and without the candidate prints
the same output.

Pre-existing defect found (not fixed, `tier0/` is read-only here): `deepcut.py` ends with `ValueError: min() iterable
argument is empty` when every anchored pattern closes (its final summary takes `min` over an empty generator, line 174),
in production and with the candidate alike.

## Not verified

- ncores=10 (the production setting) and multi-hour operation.
- Declined survivors (code 9) were exercised only through restricted `kcap`, never on real data.
- Linux/x86 build; use from threads (a mutex serializes calls).
- Tier A vertices larger than 131712 were not run end to end.
