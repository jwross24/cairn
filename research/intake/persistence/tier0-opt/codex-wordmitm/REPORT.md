# Independent word-MITM audit

Verdict: **UNRESOLVED** for the requested unconditional executable claim and the independent t347/t348 closures. The compatibility reduction is equivalent under complete, arithmetically safe execution, argued from the source, checked on 0 inputs. Identical raw child counts, diagnostic counters, ordering, and resource outcomes do not follow from that argument. Confidence: HIGH for the set argument; LOW for the two unexecuted closure checks. Nothing is PROVEN or Lean-checked.

## Evidence and scope

`A` denotes `../tierc-r2shadow/src/cport_r2.c`; `B` denotes `../sandwich-cong/src/cport_cong.c`. All line references below refer to those files. `source.diff` is the output of `diff -u A B`. Its complete contents identify the changes under review: the restriction wrapper, minimal-vector collection, empty-word shadow guard, CLI flags, and representation dump. In particular, the underlying `mitm480`, compatibility test, chain, window, and verdict bodies are identical. This is a source comparison, not runtime validation.

No `RESULT.md`, `PREDICTION.md`, or Python file in `sandwich-cong` was read. No author reasoning from that directory was used. The historical bill report and its input-generation and execution scripts were read only to establish provenance and historical commands, not as independent validation of the claim.

The manifests `INPUTS.md5` and `ARTIFACTS.md5` record explicit source, data, log, dependency, and audit artifacts. They are MD5 inventories, not correctness certificates. `ARTIFACTS.md5` excludes itself because a file cannot ordinarily contain its own content hash.

The audited C-source MD5 values are `d335e210e9eb2fee065ebbb2d78d43ec` for A and `01fe45615f7e65d5259b4f6d215b0ee3` for B (`INPUTS.md5`). `a_snapshot.c` and `b_snapshot.c` retain those source texts inside the audit directory. The explicit-input inventory does not attempt to inventory every transitive operating-system header or Python standard-library module.

## Exact sets

The statements in this section are inferred from the cited source.

A digit unit groups identical `(d,e)` pairs, with multiplicity `m_u`; an additional unit records the choice of the repunit-length residue. A digit-unit composition is a five-tuple of nonnegative counts summing to `m_u`. Its composition index identifies that tuple. The additional unit has exactly five one-hot choices. See A:2230-2258.

Let `C` be the Cartesian product of those composition-index sets. For a row `c`, let `n0_u(c)` be the first count in its digit-unit composition. Put `Q = 10^96 mod P`, where `P` is the product selected at A:2562-2575, and let `h_r = (Q^r-1)/(Q-1) mod P` for `r=0,...,4`. The source checks invertibility through `invm_gen` (A:1312-1317). The unit values are

```
v_u(c_u) = (d_u-1) * 10^e_u * sum_r n_ur(c_u) h_r mod P
v_nu(s) = (10^nu / 9) * h_s mod P
tau = -wrap / 9 mod P
```

These are exactly A:2260-2276 and A:2639-2641, with mutation flags disabled. Define

```
H = {c in C : sum_u v_u(c_u) = tau mod P}.
```

On a complete, safe MITM run, A's `G` is `H`. The Bloom stage is only a candidate prefilter: exact left sums are retained in A:2400-2410, then every equal-sum left/right combination is decoded and emitted at A:2415-2422. Different composition rows remain distinct even if their values collide. A constructs `GInfo` for every row of `H` at A:2649-2672, including rows incompatible with every word.

Let `W` contain the depth-1 words with `wok[wi] != 0`, additionally restricted by `--word-only` if supplied. Each word has a vector `f_w(u)` counting its fixed digit occurrences in unit `u`; the additional unit's entry is zero. At depth 1 a fixed digit has `t=0`, because `dc_stage` sets `t=D-1` and is called once (A:773, 2554-2555). Fixed masks and word admission are A:2592-2615. The precise pairs reaching `chain480` in A are

```
Pairs_A = {(w,c) : w in W, c in H,
                     n0_u(c) >= f_w(u) for every digit unit u}.
```

This follows directly from A:2677-2692. Thus the raw `GInfo` child set and the pair set consumed by `chain480` are different questions.

B computes the vector family `F` over all `wok` words, even when `--word-only` selects one word. It retains the componentwise minimal distinct vectors `M`, using the earliest occurrence to represent equal vectors (B:2703-2727). Its returned child set is

```
H_B = union_{f in M} {c in H : n0_u(c) >= f(u) for every digit unit u}.
```

B:2473-2492 makes each restricted coordinate list, preserving original values and an explicit index map; B:2495-2501 maps every MITM result back to original composition indices. The original composition arrays are shared read-only; restricted searches use only `nc` and `val` (A:2281-2300, 2343-2422). No composition count or value is recomputed under a different meaning.

## Minimality and pair equality

The following is a source argument, not a formal proof.

1. A strictly smaller vector removes a larger vector. An equal vector removes only its later copies (B:2713-2723). Consequently equality cannot remove every representative of a minimum, and strict componentwise descent cannot cycle in the finite family.
2. For every `f in F`, there is a retained `m in M` with `m <= f`. One can choose a minimal vector in the nonempty finite subfamily below `f`, then its earliest duplicate. Any vector that could remove it is also below `f`, contradicting that choice.
3. If a child is compatible with a discarded word, then `n0(c) >= f >= m`. It therefore appears in the search for `m`. A child compatible with a non-minimal word but no minimal vector is impossible under these definitions.
4. Every row B returns is in `H`; every `(word, child)` pair admitted by A has its child in `H_B`. The unchanged compatibility test in B:2767-2782 consequently gives `Pairs_B = Pairs_A`.

`--word-only` does not invalidate the argument: collecting minima from more words can retain extra children, but the selected word's vector is still dominated by some retained minimum, and the downstream selected-word test remains in place.

B's sort uses `memcmp` on whole rows (A:2429-2430; B:2508-2518). This is a total byte ordering on this executable's fixed-width row representation, not necessarily numeric lexicographic order. Equal rows become adjacent, and the deduplication removes exactly equal index rows. Duplicate vectors and overlap between different restricted searches cannot multiply downstream pairs. A emits each row once through its unique left/right decomposition; B restores that multiplicity to one.

## What equality does and does not imply

The following are inferred from source.

For complete, safe runs, the same admitted pairs produce the same mathematical `V`, word coset, prime intersections, window choices, and minimum `nn`: A:2655-2670, 2691-2725; identical bodies in B:2745-2759, 2781 onward. The per-child caches store targets determined by that child's `V` and `a`, not by traversal order (A:2474-2490, 1488-1502). The minimum operation and additive semantic counters are order independent. Thus compatibility, non-shadow compatibility, chain passes, windows, alive windows, alive words, and the exact sandwich decision agree if neither execution stops at a resource limit. The sandwich comparison is exact integer arithmetic at A:1016-1022, not its floating-point display.

However, `H_B` need not equal `H`: globally incompatible children are intentionally omitted. A computes `rr.nG = |H|`; B computes `rr.nG = |H_B|` (A:2642; B:2732). The work-space counter is also defined differently: A uses the full Cartesian product (A:2349-2350); B sums restricted product sizes, counting overlaps (B:2496, 2520). Bloom candidates, left/right sizes, and true matches in B's verbose MITM line describe its final constituent call, not the union (A:2358, 2399, 2424; B:2733). No identical-counters claim is justified for these diagnostics.

Sorting changes child indices and therefore `g%d` point tags and dump order (A:2726-2728). It can also change the verbose last-killer diagnostic (A:2683, 2741). These are observable differences even when the semantic pair set agrees. No concrete full-program input exhibiting a counter difference was executed in this audit.

The `--brute480` diagnostic is not adapted to B's restricted set: B:2734-2736 still compares it with the exhaustive *unrestricted* set using A:2439-2455. When the restriction removes any row, that diagnostic comparison must disagree. This is a conditional source observation, not an executed counterexample.

## Candidate cap and other resource outcomes

At A:2393, exceeding capacity `2^26` calls `die`, which prints `FATAL` and exits 2 (A:37). This is not a returned `BUDGET` verdict. A returned budget from the earlier space/right caps is a different path (A:2351, 2359, 2641, 2770). The historical raised runs also record `ERROR`, not a verdict, for both target cases (`results_raised3.jsonl`:90,92).

B can complete when A exceeds a cap because it enumerates smaller Cartesian products. A cap abort is not an A certificate that B contradicts. Provided *all* restricted calls complete, the union argument supplies completeness independently of A's ability to finish; exact verification remains inside every call. If a restricted call returns budget, B returns budget and the caller exits before processing the accumulated partial union (B:2506, 2731). A candidate-cap `die` also prevents any final verdict. B does not silently accept a truncated search on these paths.

An unconditional claim of identical executable verdicts is therefore too broad: different work domains can encounter different space/right/candidate caps. No runtime instance of that distinction was independently reproduced here.

Raising only the candidate cap is not a demonstrated route within 2 GB. A `Cand` contains two 64-bit values (A:2316); `2^26` entries request 1 GiB, and the next capacity requests 2 GiB before considering other allocations. The exact-verification hash table requests a power-of-two slot count exceeding `4*ncand+16`, at eight bytes per slot (A:2400-2401), while candidates remain allocated. Those requested sizes already exceed the memory budget near the original cap. These are allocation-size calculations, not measured RSS. Compression and residency must not be inferred from allocation size.

`a_full.c` and `a_full.diff` prepare an alternative through A's full, unrestricted child space: increase Bloom sizing from 40 to 160 bits per left entry, with a maximum of `2^33` bits, and print progress. The candidate cap and exact verification are retained. This changes the false-positive prefilter only in the source argument (A:2309-2314, 2390-2392), without using any word restriction. It is an unvalidated experimental build; its fit below 2 GB and its runtime are unmeasured.

## Wraps, non-shadow children, and arithmetic limits

The source requires `V-y` to be a nonnegative integer multiple of `R_96` (A:2583-2589), and the target is `-wrap/9 mod P`, not universally zero (A:2639). The containment/minimality argument works for every target residue. It does not assume wrap zero or restrict children to shadows.

The all-residue-zero composition is compatible with every actual fixed vector, because `f_u <= m_u`. Its value is zero. If `tau=0` and there is a passing word, B must retain it. When no word passes, B returns an empty union and suppresses the zero-target shadow assertion (B:2725-2727, 2764); there are no consumed pairs in that case. A can still do unnecessary MITM work or encounter a cap. For nonzero targets the shadow cannot belong to `H`; non-shadow rows are otherwise handled identically (A:2663-2675, 2690, 2721). These are source deductions, with no independent wrap-positive execution here.

The arithmetic qualification is material. The rep-file parser accepts up to 64 digits, but the initial depth stage returns budget above 31 free digits before producing words (A:2888, 721). Thus a normal representation reaching this optimization has at most 31 digits. Its fixed counts fit in `unsigned char`, its masks fit in 32-bit `unsigned`, and even a multiplicity-31 composition-count numerator fits in signed `int` (A:2231, 2595; B:2705-2710). Composition indices and allocation/count bounds still require valid memory sizes.

The modulus guard permits values up to approximately `1.8e19`, which is larger than `2^63` (A:2570). It does not establish that `sg + count*geo`, pairwise sums, or `target + P - sum` fit in `u64` (A:2274, 2287-2296, 2384-2385). `mulm` uses a 128-bit product (A:1305), but those additions and the count multiplication do not. A conservative sufficient bound for these particular operations with at most 31 digits is `32*P < 2^64`; it is not enforced by that guard. Right-space products and decoding indices likewise use unchecked `u64` multiplication (A:2353-2363), and `G.n` is narrowed to `int` (A:2649; B:2739). Allocation failures are mostly unchecked (A:2303, 2393, 2401; B:2474-2487). This audit does not assert those conditions occur for the shipped target cases. It also does not extend the equivalence argument to overflow, invalid inputs, allocation failure, or arbitrary raised caps.

## t347 and t348 provenance and outcome

Verified by file-reading commands:

* `pattern_t347.txt` records `pat_b3.jsonl`:1576951, with `y=28342368844941312`, `nu=6`, and 31 digit entries. `pattern_t348.txt` records `pat_b3.jsonl`:1462085, with `y=133995176056631232`, `nu=18`, and 31 digit entries. The sampler's literal `k` field is zero; the actual 31-entry vectors are the relevant input. `target_survivors.txt` records the matching survivor rows 150 and 143, which carry `k=31` and the source name. These extractions used literal full digit-vector matches, not an inference from a zero field.
* `data/survivors_meta_b3.tsv`:348-349 identifies those rows as t347/t348. `mk_reps2.py`:11-22 explains the ID assignment and columns: `nodes` is not the sampler's `total`. An initial search confusing those columns returned no matches; it supplied no evidence of missing inputs.
* The exact normalized rep-file lines are:

```
28342368844941312 6 31 2:0 2:6 2:6 2:11 3:2 3:5 3:5 3:5 3:5 3:6 3:7 3:7 3:8 3:8 3:8 3:8 3:9 3:9 3:9 3:9 3:10 3:10 3:10 3:11 3:12 3:14 3:16 4:4 7:13 9:13 9:15
133995176056631232 18 31 2:0 2:2 3:1 3:4 3:5 3:5 3:6 3:6 3:7 3:7 3:8 3:8 3:8 3:9 3:9 3:10 3:10 3:10 3:12 3:12 3:13 3:13 3:13 3:13 3:14 3:15 3:16 4:5 4:8 7:14 9:5
```

The historical commands in `results_raised3.jsonl`:90,92 invoke `tierc-r2shadow/cport_r2c shadow480`, the corresponding rep file, `lattice96.txt`, `levelprimes480.txt`, `utable_u2_k34.txt`, and `--mitm-space-cap 1e30 --mitm-right-cap 1e14`. `run_jobs.py`:4-9,29-41 establishes those paths and execution settings. Its historical process uses a 4 GB guard, not this audit's 2 GB limit.

The default logs report full spaces `3.297e18` and `1.59e19`, respectively, then `VERDICT BUDGET`. The raised logs print `FATAL: mitm480: candidate list too large`. The recorded historical CPU times are 1445.442782 and 2580.6204 seconds. These are observations of existing logs, not independently rerun measurements.

**Independent outcomes: t347 UNRESOLVED; t348 UNRESOLVED.** Neither requested bound, `10^300.68` nor `10^301.19` in digit-count units, was independently confirmed or refuted. The formatter actually prints `bound 10^(10^...)` for the corresponding integer-size lower bound, with the outer digit-count exponent displayed separately in tierc mode (A:497-504, 2869-2870, 2920). A notation-only comparison must distinguish those quantities.

## Runtime limitation and reproducibility

The prepared builds used this command shape, with logs retained for all three builds:

```sh
nice -n 10 clang -O3 -I/opt/homebrew/include -L/opt/homebrew/lib research/intake/persistence/tier0-opt/codex-wordmitm/a_full.c -lgmp -lm -o research/intake/persistence/tier0-opt/codex-wordmitm/a_full
```

`build_a.log`, `build_original.log`, and `build_b.log` report:

```
nice: setpriority: Operation not permitted
```

The compiler commands exited 0 and produced binaries, but priority enforcement was not established. A direct invocation of `nice -n 10 .../a_original` also printed that error and the program's usage, exiting 2 (`runtime_probe.out`, `runtime_probe.exit`). Thus wrapping a command in `nice` is not evidence that this sandbox honored the requested priority.

The initial control supervisor was invoked exclusively as:

```sh
UV_CACHE_DIR="$PWD/research/intake/persistence/tier0-opt/codex-wordmitm/uv-cache" UV_PYTHON_DOWNLOADS=never nice -n 10 uv run --no-project python -I research/intake/persistence/tier0-opt/codex-wordmitm/run_guard.py controls
```

It exited 1; `controls.driver.log` records `PermissionError: [Errno 1] Operation not permitted: 'ps'`. Its partial control output contains no verdict and is not a checked input. The supervisor source replaces that blocked monitoring path with a CPU limit, but does not implement a replacement RSS guard and is not a ready-to-run solution to the audit constraints.

No long target compute was launched after these failures. The required priority could not be honored, RSS monitoring through `ps` was blocked, and a safe internal memory guard was not validated. Permission to relax priority was requested and was not received at report preparation. The two-CPU-hour allowance was not spent; this is an environment limitation, not a measured timeout or an assertion that all independent algorithms would exceed two hours. No processes belonging to others were touched.

The concrete remaining work is to run the full-domain A route in an environment that honors priority and enforces the RSS bound, validate its changed Bloom filter against exhaustive small cases, complete both targets, and compare semantic point sets and exact minimum norms with B. The source argument alone does not replace that independent experimental check.
