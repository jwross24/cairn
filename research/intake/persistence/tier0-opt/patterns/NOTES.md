# Full open-pattern record (untracked research code)

Each equation record (`trees_*.jsonl.eqs.jsonl` and the `eqs` list inside every vertex row) gains one trailing key,
`open_patterns`; every existing key, its value and its order are unchanged.

```
"open_patterns": {"level": 96, "M": [..], "items": [{"a": int, "nu": int, "eps": [int per M entry, M sorted],
                  "v0": [b, c], "u1": [b, c], "u2": [b, c]}, ...]}
```

`(a, nu, eps)` are residues mod `level`, `eps[j]` belongs to `M[j]`, and the coset is `v0 + Z u1 + Z u2` in the exponents
(b, c) of `2^a 3^b 7^c`. `items` is in the order of the `exceptional` and `bounds` lists (index i of each describes the
same pattern); an equation with no open pattern carries `items: []`. Rows written before the swap lack the key: every
consumer reads rows by name (`deepcut.py`, `sandwich.py`, `classify_open.py`, the resume logic), so read it with
`d.get('open_patterns')`.

## Where patterns were dropped

`run_c.run` (tier0/run_c.py) holds `r['open']`, a list of `(a, nu, eps, Coset)`, and reduces it to `r['bounds']` and
`r['exceptional']` in the loop that ends at `r['exceptional'].append`. `run_trees_c_v2.py` copies those two into the
row. The change adds `r['open_patterns']` right after that loop (`run_c.py:109`) and one keyword in the row
(`run_trees_c_v2.py:68`). `run_vertex_c.py` is deliberately not edited: gatev2 compares its rows ref vs candidate, so a
new key there would fail the gate.

## Files and base

Candidates: `run_c.py` (base md5 `3e2a14e700062cf55faba8d8ef739c09`), `run_trees_c_v2.py` (base
`49db3b31dfa2f04c811841d18117bf01`). Both bases are the current `tier0/` files (the pydesc swap is already in place;
`tier0v2.py 2dd0ee1123def50fd46974f2f9205c16` is untouched). Candidate md5: `run_c.py 9ccbe990096113f775b0d34794925d76`,
`run_trees_c_v2.py 9fe1a694f68b7ea41394464d6958ce3b`. `BASE-MD5.txt` lists the base md5s.

## Swap procedure (not performed)

```
P=/Users/jwross/Documents/cairn/research/intake/persistence
cd $P/tier0 && md5 -q run_c.py run_trees_c_v2.py     # must print the two base md5s; otherwise rebase the 2-line change
mkdir -p $P/tier0-opt/patterns/backup-pre-swap
cp -p $P/tier0/run_c.py $P/tier0/run_trees_c_v2.py $P/tier0-opt/patterns/backup-pre-swap/
cp -p $P/tier0-opt/patterns/run_c.py $P/tier0-opt/patterns/run_trees_c_v2.py $P/tier0/
cd $P/tier0 && uv run --no-project --with gmpy2 --with sympy python -c "import run_c, ast; ast.parse(open('run_trees_c_v2.py').read()); print('ok')"
```

Relaunch: stop the running `run_trees_c_v2.py` (or let it finish the equation in flight; rows already written stay), then
start the same command line again (`uv run --no-project --with gmpy2 python run_trees_c_v2.py zf_below_1e4000.txt
trees_mac.jsonl 10 2e13 runall_final.jsonl trees_c.jsonl`). It resumes from `trees_mac.jsonl.eqs.jsonl`: finished
equations keep their old rows (no field) and new ones carry it; a vertex row mixing both is valid. A running process keeps
the old modules in memory, so the field appears only after the restart. Rollback: copy the two files back from
`backup-pre-swap/`; rows already written keep their extra key, which every consumer ignores.

## Backfill for equations finished before the swap

`tools/backfill.py <src-dir> <eqs.jsonl> <zf list> <out.jsonl> [--vertex S ...] [--max-npat N] [--ncores 2] [--dry]`
reruns only the equations whose row has `open > 0` and no field (closed equations are skipped), through `<src-dir>`'s
`run_c.run`, writes a sidecar row `{s, M, consistent, open_patterns, secs}` and never touches the sweep files. A row is
`consistent` only when the rerun reproduces the recorded `open`, `bounds` and `exceptional`; otherwise `open_patterns`
is null. Resumable by (s, M). `--dry` prints the work.

Cost: the level-12 pass cannot be restricted to the open patterns (their level-12 ancestors are unknown), so the cost is
that of rerunning the equations with open patterns. Measured at nice 10, 2 cores, machine load about 45 on 10 cores
(wall time is a floor on throughput, not final): vertex 14336, 12 equations, 1.67e9 level-12 patterns, 31 open patterns,
8.4 s wall, 7.4 s user, about 2.2e8 patterns per CPU second; single equations 1.2 to 1.5 s. The 754 equations with open
patterns in `trees_mac.jsonl.eqs.jsonl` hold 1.11e12 level-12 patterns, so about 5,000 CPU seconds if the rate holds
(extrapolated; larger vertices were not timed, 131712 took 25 s for 15 equations). Not run for all.

## Gate record

Scratch: `/private/tmp/persist-patterns/` (prod = copy of current tier0, cand = prod + the two candidates).
Drivers in `tools/` (`vertex_gate.py`, `trees_gate.py`, `mutant_gate.py`, `gatev2_dylib_src.patch`).

- Vertices 72, 224, 14336, 10800, 131712 (`tools/vertex_rows.py`, 3 cores, PYTHONHASHSEED=0): rows equal production on
  every existing field (9, 5, 16, 17, 15 rows). The harness equals the real `run_vertex_c.py` output on 14336.
- Round trip (`tools/roundtrip.py`, independent of run_c): 62 equations, 117 open patterns, 0 bad. It checks
  `len(items) == open`, `bounds` and `exceptional` recomputed from the coset, and that each `(a, nu, eps)` is consistent
  with its coset modulo every prime of `10^level - 1` (v0 hits the pattern residue, u1 and u2 lie in the kernel).
- Planted mutant (eps of the next open pattern recorded, or shifted by one for a lone pattern): 23 of 31 open equations
  and 91 patterns flagged, exit 1. The 8 unflagged equations hold patterns whose eps coincide.
- `run_trees_c_v2.py` on the 14336 mini list: `.jsonl` and `.eqs.jsonl` equal production minus the new key, also when
  the eqs file is seeded with 8 legacy rows (mixed rows); round trip 64 equations (8 legacy), 0 bad; `classify_open.py`
  and `deepcut.py --depth 1` output equals production apart from the file name and the timing bracket.
- gatev2 `--fast --jobs 2` with the overlay (`gate-overlay/`: both candidates plus `libpydesc.dylib`): PASS, 21/21
  plants. Because `tier0/` now holds `pydesc.py`, gatev2's reference pipeline also needs the dylib; the scratch copy
  `/private/tmp/persist-patterns/gatev2x` adds `*.dylib` to `setup_work` (`tools/gatev2_dylib_src.patch`). The shared
  `/private/tmp/persist-pydesc/gatev2x` lacks it and fails the ref pipeline.

## Not verified

ncores=10 and multi-hour operation; the full gatev2 (default stage); equations with more than 96 open patterns
(max seen 72); row size growth at full scale; the backfill on any vertex above 14336.
