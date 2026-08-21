## franken_markdown v0.3.4 (@ 562f4bd91dcf)

**What it actually is.** A clean-room, `#![forbid(unsafe_code)]`, zero-dependency (core) Rust Markdown -> HTML/PDF renderer with an agent-first CLI (`fmd`). ~64K lines in `src/` (33.6K of it `src/pdf.rs`), ~1,800 `#[test]` functions, no `[dev-dependencies]`, no `todo!()`/`unimplemented!()`. It is mature as a renderer and unusually heavy on verification machinery: a ratcheted CommonMark conformance harness, seeded in-tree fuzz, metamorphic tests, byte-level goldens, a README-claims registry gate, mutation/coverage ratchets, and a perf-proof checklist — all wired into `.github/workflows/ci.yml`. Nothing in it is mathematical or a parser Cairn needs; the borrowable material is test/gate *patterns*.

**README vs code**
- "ratcheted CommonMark 0.31.2 conformance floor" -> true and honest: 379/652 (58.1%) normalized match, floor file `tests/fixtures/commonmark/conformance-floor.txt` (=379), per-section table in `conformance-summary.md`; harness is `scripts/commonmark-conformance.sh:57-164`; the floor is also self-advertised in `fmd capabilities --json` (`src/cli.rs:1571`, `commonmark_spec: 0.31.2_ratcheted_min_379_of_652_normalized`) and the harness fails if flag and floor disagree (`commonmark-conformance.sh:148-160`).
- `tests/parser_differential.rs` is NOT differential testing against a reference implementation: it diffs against approved checked-in snapshots (`tests/parser_differential.rs:1-6, 27-55`). Real cross-implementation differential is only native-vs-WASM byte parity of the same engine (`scripts/check-wasm-package.sh:115-143`).
- "Fuzz" (docs/TESTING.md:62) -> seeded LCG generators in a plain `#[test]`, explicitly not coverage-guided and no fuzz crate (`tests/parser_fuzz.rs:3-5, 27-48`).
- "zero third-party dependencies" engine -> `Cargo.toml` has only optional `clap`/`wasm-bindgen`/`asupersync`; enforced by `scripts/check-policy.sh:21-27` (cargo tree of `--no-default-features` must be exactly one line).
- "deterministic PDF" -> no wall clock in the core: Info date defaults to epoch 0 (`src/pdf.rs:26017-26019`); `SOURCE_DATE_EPOCH` is parsed only at the CLI boundary (`src/cli.rs:1372-1392`); `Instant::now()` in core is profiler-only and cfg'd off on wasm (`src/parse/mod.rs:197-205`, `src/pdf.rs:2213-2220`).
- "mutation-tested" -> ratcheted, but scope is three small files (`scripts/mutation.sh:35`, ceiling 0).
- Clone has a single commit; no history-based maturity evidence.

### M1. Conformance corpus + ratcheted floor + per-example ledger + self-advertised floor
- **Mechanism.** Vendored official corpus `tests/fixtures/commonmark/spec.json` (652 x `{markdown, html, example, section}`), README with provenance/version/date. Harness renders each example through the *release binary*, normalizes (strip wrapper/ids/spans: `commonmark-conformance.sh:68-78`), classifies each example `pass | intentional_non_goal | known_gap` (`:95-107`), writes `ledger.tsv` + `summary.md` per run-id (`:114-126`), prints worst-section-first, and enforces a committed integer floor that only `--update-floor` may raise (`:136-146`). Drift guard: the tool's own `capabilities --json` must advertise the floor (`:148-160`). Same ratchet shape for coverage (`scripts/coverage.sh:35-39`, floor file `tests/fixtures/coverage/coverage-floor.txt`) and mutation survivors (`scripts/mutation.sh:9-13, 37-38`).
- **Candidate home.** skill interface + self-tests (known-answer self-test corpus format + scoreboard); secondarily gate layer: small-scale ladder (per-toy-curve ledger with ratcheted pass floor).
- **Cost.** ~150 lines bash+python; python3 at test time; a committed floor file and summary snapshot per skill.
- **Evidence.** STRONG-EMPIRICAL — implementation read end to end, wired into CI (`.github/workflows/ci.yml:59-60`), committed artifacts exist; but unlike the other gates it ships no `--self-test` proving the normalizer/ratchet has teeth.
- **Epistemics risk.** none if the floor is a *lower bound* and `intentional_non_goal` is a fixed, declared set (here `INTENTIONAL = {...}` at `:66`); risk if an orchestrator could edit the non-goal set — keep it in the immutable gate config.

### M2. Claims registry with proof pointer + gate self-test that plants an overclaim
- **Mechanism.** `scripts/claims.tsv` rows `label / readme_pattern / capability_key / expected_substr / proof_path`. Gate enforces a row only when the README actually makes the claim (`check-claim-discipline.sh:57-71`), requires the tool's machine-readable capabilities to agree and the proof artifact to exist. Test-rigor cross-check: a marketed coverage % may not exceed the committed measured baseline (`:79-96`). `--self-test` proves teeth by appending an impossible claim + synthetic registry row and asserting FAIL (`:110-144`); CI runs the self-test (`ci.yml:44-45`).
- **Candidate home.** claims DB (calibration tag + evidence pointer) / calibration layer: every claim row carries an evidence pointer that must resolve; a "tag ≤ evidence" check analogous to "claimed % ≤ measured %".
- **Cost.** A TSV + ~100 lines bash; grep-based claim detection is coarse.
- **Evidence.** PROVEN-in-source (`check-claim-discipline.sh:51-73, 110-144`).
- **Epistemics risk.** none — it strengthens "every claim tagged with evidence". Keep registry edits out of orchestrator reach.

### M3. "Prove the gate has teeth" self-tests for every gate script
- **Mechanism.** Each gate script has a `--self-test` mode that (1) plants a violation and asserts detection, (2) plants an allowlisted case and asserts pass, (3) runs on the live tree. E.g. `check-test-doubles.sh:83-105` plants `struct EvilMock;`; `mutation.sh:71-89` feeds a synthetic `outcomes.json`; `claim-discipline` as above. CI runs the self-tests before the real gate (`ci.yml:44-60, 159-165, 183-191`). `scripts/test-all.sh:32-49, 82-110` runs every gate with per-gate rc/timing and a combined report (exit 70 on any failure).
- **Candidate home.** gate layer: every gate (verifier, ladder, no-go checklist, tier gate) ships a planted-failure self-test; also the skill known-answer self-test.
- **Cost.** One negative fixture per gate; trivial.
- **Evidence.** PROVEN-in-source (files/lines above).
- **Epistemics risk.** none; it is the mechanical defense against silent-fail-open gates.

### M4. Seeded deterministic fuzz + invariant battery + pathological regression guards
- **Mechanism.** LCG PRNG (`tests/parser_fuzz.rs:27-48`), three generators (markdown-ish soup over-weighting structural bytes, raw byte soup via `from_utf8_lossy`, escalating nesting `:56-88, 159-180`), one `assert_robust` battery under `catch_unwind`: never panics, spans balanced and on char boundaries, render never errors (`:96-135`). Named DoS regressions encoded as "the test completes" (`:182-220`). Metamorphic suite: equivalent-source invariants (CRLF/BOM/ref position/label case) and injection-safety over generated docs (`tests/parser_metamorphic.rs:95-127, 153-186`).
- **Candidate home.** skill interface + self-tests (any skill that parses untrusted text: Librarian extraction, Formalizer statement parsers); gate layer: submission verifier robustness.
- **Cost.** ~250 lines std-only Rust; not coverage-guided, so weaker than cargo-fuzz for bug discovery.
- **Evidence.** PROVEN-in-source (runs under `cargo test`, `ci.yml:62-63`).
- **Epistemics risk.** none.

### M5. Golden snapshot = fingerprint + human-reviewable excerpt, regenerate-by-env
- **Mechanism.** Snapshot file holds `bytes=`, 64-bit `fingerprint=`, then the normalized body; any byte drift moves the fingerprint while the diff stays reviewable (`tests/golden_output.rs:69-101`). PDF snapshot = bytes/fingerprint/page-count/object-count (`:90-101`). `UPDATE_GOLDEN=1` rewrites (`:57-59, 121-123`). Layout render-tree goldens pinned on Linux only because f32 positions (`src/pdf.rs` render_tree_golden_tests doc, `cfg(all(test, target_os = "linux"))`).
- **Candidate home.** skill self-tests (known-answer output pinning for non-replayable-but-deterministic skills); reproducibility gate.
- **Cost.** Trivial. Gotcha: fingerprint uses `std::collections::hash_map::DefaultHasher` (`:61-67`) — deterministic today but the algorithm is not a stability guarantee across Rust versions; **not** a content-address.
- **Evidence.** PROVEN-in-source.
- **Epistemics risk.** `UPDATE_GOLDEN` leaking into a CI env would silently rewrite and pass; keep regenerate modes out of the gate environment.

### M6. Determinism by construction + byte-identical re-render assertions + cross-target parity
- **Mechanism.** Core never reads env/clock (epoch default 0, explicit `metadata_epoch_seconds`, `src/lib.rs:273-278`). Every corpus test re-renders and asserts `==` bytes (`tests/corpus_soak.rs:92-96`, `parser_metamorphic.rs:221-223`); CLI-level double-run `cmp` on JSON surfaces/HTML/PDF (`scripts/check-determinism.sh:37-83`); WASM vs native byte parity with pinned epoch (`check-wasm-package.sh:121-143`).
- **Candidate home.** substrate (content-addressing needs deterministic artifacts) and reproducibility gate (re-run == same hash as admission check).
- **Cost.** Discipline more than code; one double-run assertion per skill self-test.
- **Evidence.** STRONG-EMPIRICAL — assertions read; cannot verify 33K-line pdf.rs has no hidden nondeterminism.
- **Epistemics risk.** none.

### M7. Timing-free, input-ordered, schema-versioned receipt with per-output fingerprints
- **Mechanism.** `BatchReceipt::to_json` hand-rolled stable key order, `"schema":"fmd-batch-receipt-v1"`, per-output `{path, bytes, fnv1a64}`, files in sorted input order regardless of worker completion, no timestamps (`src/batch.rs:274-368`); tested byte-identical across two parallel runs (`:1382-1431`). PDF `/ID` is a domain-separated FNV over trailer-relevant bytes (`src/pdf.rs:25942-25962`).
- **Candidate home.** substrate (run receipt shape) / tier scheduler (batch receipts); the fingerprint itself must be swapped for a cryptographic hash — FNV-1a is declared non-cryptographic (`batch.rs:233-235`).
- **Cost.** Trivial pattern.
- **Evidence.** PROVEN-in-source.
- **Epistemics risk.** none.

### M8. Machine-checked optimization-proof document + variance-envelope perf classifier
- **Mechanism.** A perf claim must ship a proof file with required lines (before/after p95 with units regex, golden checksum, determinism run, no-default build, rollback plan) and no unresolved template placeholders (`scripts/check-optimization-proof.sh:94-163`; fixture `tests/fixtures/optimization_proof/valid.md`). `perf-compare.sh` classifies per-scenario p95 deltas against an envelope (default ±3%) as noise/improvement/regression, reports hotspot shift and next target, JSON or table (`:107-175`); artifact schema `fmd-perf-artifact-v1` (`docs/PERFORMANCE_ARTIFACT_SCHEMA.md`).
- **Candidate home.** tier scheduler/cost profiles (predicted-vs-measured cost evidence before a cost profile may be revised) and small-scale ladder "measured scaling" (a speedup claim needs an artifact, a checksum, an envelope).
- **Cost.** Bash+python; the field list is project-specific and would be rewritten.
- **Evidence.** STRONG-EMPIRICAL — scripts and sample artifacts read (`tests/artifacts/perf/qw1.8.4-compare/*`); `--self-test` exists (`ci.yml:50-51`) but was not read.
- **Epistemics risk.** none; it forces evidence for performance claims.

**Verdict.** The renderer itself is irrelevant to Cairn. The single most accretive thing is the *combination* M1+M2+M3: a vendored known-answer corpus with a per-example ledger and a committed ratcheted floor that the tool must itself advertise, plus a claims registry whose every row points at a proof artifact, plus a planted-failure self-test for every gate. Everything else (M4-M8) is a small, sound pattern Cairn would re-implement in a few dozen lines; none is a dependency candidate.

**Gotchas.**
- License is "MIT with OpenAI/Anthropic Rider" (`LICENSE:1-40`): restricted parties get no rights and "use" includes testing/analyzing/incorporating into evaluation harnesses. Borrow *patterns* re-implemented from scratch; do not vendor code.
- Fingerprints: `DefaultHasher` (golden) and FNV-1a (receipts, PDF /ID) are non-cryptographic/non-stable; Cairn's substrate must not copy them.
- Harness logic is Python-in-bash heredocs with fmd-specific normalization regexes; only the *shape* transfers.
- Float-bearing goldens are pinned per-platform (Linux); a ladder that emits floats needs the same pin.
- M1 has no self-test; M5 regenerate env var neuters the gate if present.

**Sources.** `scripts/commonmark-conformance.sh:57-164`; `tests/fixtures/commonmark/{README.md,conformance-floor.txt,conformance-summary.md}`; `src/cli.rs:1571,1372-1392`; `scripts/check-claim-discipline.sh:51-157`; `scripts/claims.tsv`; `scripts/check-test-doubles.sh:83-105`; `scripts/mutation.sh:9-13,35-38,71-89`; `scripts/coverage.sh:35-39`; `scripts/test-all.sh:32-110`; `tests/parser_fuzz.rs:27-249`; `tests/parser_metamorphic.rs:95-243`; `tests/golden_output.rs:57-156`; `tests/corpus_soak.rs:60-96`; `tests/parser_differential.rs:1-55`; `scripts/check-determinism.sh:37-83`; `scripts/check-wasm-package.sh:115-150`; `src/pdf.rs:25942-26019,2213-2220`; `src/parse/mod.rs:197-205`; `src/lib.rs:27,273-278`; `src/batch.rs:1-16,274-368,1382-1431`; `scripts/check-optimization-proof.sh:94-163`; `scripts/perf-compare.sh:46-175`; `scripts/check-policy.sh:21-27`; `.github/workflows/ci.yml:13-191`; `Cargo.toml`; `LICENSE:1-40`.
