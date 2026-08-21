## frankensqlite v0.3.7 (@ 9b1d3ed7b3cb)

**What it actually is.** A 1.64M-line, 27-crate, agent-swarm-built ("beads") ground-up Rust SQLite reimplementation with a real page-level MVCC/SSI engine (`fsqlite-mvcc`, 110K lines) wired into `fsqlite-core::Connection`, plus a very large verification harness (`fsqlite-harness` 293K + `fsqlite-e2e` 237K lines). Tested by 23,773 `#[test]` functions, proptest in 117 files, one loom *model*, a small fuzz dir (5 targets), 35 conformance JSON fixtures, and differential runs against `rusqlite`. RaptorQ, the e-process core, and the deterministic scheduler all live in the author's separate `asupersync` crate (crates.io 0.4.8, not vendored), so those are dependency-only from this repo's point of view.

**README vs code**
- "Page-level MVCC concurrent writers, SSI by default" -> real: `crates/fsqlite-mvcc/src/ssi_validation.rs:738-960` (Cahill/Fekete pivot rule, proof-carrying), visibility predicate `invariants.rs:217-220`. But `docs/concurrency-contract.md:18-32`: >=10 implicit-autocommit writers reproduce corruption (P0 `bd-9inpb` open); "treat >=10 concurrent writers as unsupported".
- "RaptorQ is research, not live" -> confirmed: codec is `asupersync::raptorq` (`fsqlite-core/src/raptorq_codec.rs:17-29`); `WalBackendAdapter::with_fec_hook` (`fsqlite-core/src/wal_adapter.rs:304`) has zero callers; no caller of `recover_wal_fec_group/append_wal_fec_group/scan_wal_fec` outside `wal_fec.rs` except `lib.rs` re-exports.
- "unsafe only in VFS + C ABI" -> `Cargo.toml:48 unsafe_code = "forbid"`, per-crate `allow` in `fsqlite-vfs/Cargo.toml:44`, `fsqlite-c-api/Cargo.toml:30`. Consistent.
- "`PRAGMA fsqlite.write_merge` is an SSI-validation switch (SAFE/LAB_UNSAFE)" -> `fsqlite-core/src/connection.rs:2570-2598`, gate consulted at `:64994`, forced off under SAFE at `:71688-71694`. Consistent.
- In-repo doc drift: `drift_monitor.rs:10-13` says "BOCPD regime classification"; the `DriftDetector` is an EMA threshold detector (`replay_harness.rs:788-845`). Real BOCPD exists (`fsqlite-mvcc/src/bocpd.rs`) but is consumed only inside `fsqlite-mvcc` (dormant).
- Parity "proof obligations" are hand-stamped `ObligationStatus::Verified` with `artifacts: Vec::new()` (`parity_invariant_catalog.rs` `unit_obligation`/`differential_obligation` helpers); `validate()` never checks that `test_path` exists or passed; `Waived` counts as satisfied (`:133`, `confidence_gates.rs:72-83` default `waived_obligations_satisfy_gate: true`).
- Stale test comment: `fsqlite-e2e/tests/correctness_concurrent_writes.rs:9-12` says the MVCC writer path "is not yet wired to the persistence layer", contradicting the concurrency contract. Harness is declared the source of truth (`concurrency-contract.md:52-70`).

### M1. Negative-results ledger + machine-readable dead-end preflight gate
- Mechanism: 22,141-line `docs/progress/perf-negative-results.md` (583 entries, each with target, evidence, A/A null control, result, and a concrete *retry condition*). `fsqlite-harness/src/sql_pipeline_optimization.rs:733-797` parses it into `CandidateRecord{key, decision, null_control_recorded, retry_condition, evidence_refs}` and answers `Allowed | Blocked | RequiresNullControl` for a proposed candidate; `Blocked` forbids source edits, `RequiresNullControl` means "the prior REJECT had no A/A null, rerun it before proposing anything new". `docs/LEDGER_RESURRECTION.md:40-130` adds a six-class adjudication of negative results (VALID-PROFILE / VALID-MECHANISM / VALID-AB / VOID-CV / VOID-ZEROSELF / VOID-NONULL) plus "baseline-drift provisional", and the rule that mechanical void-screens only build a reading queue, never a verdict. Entries carry exact dispatch counts as a reachability gate (zero dispatch -> `reachability_gate=INVALID`, timing not interpreted; `perf-negative-results.md:1047-1120`).
- Home: dead-end ledger (Blocked ~ REFUTED; RequiresNullControl ~ PARKED-pending-better-measurement) and negative-results map; the reachability gate maps to the no-go checklist.
- Cost: the parser is string-heuristic over markdown (`build_candidate_record_from_ledger_entry`, `entry_records_null_control`), fragile; Cairn should store structured records and borrow the state machine, not the parser.
- Evidence: PROVEN-in-source for the gate (`tests 1318-1438`, e.g. `candidate_preflight_requires_null_control_for_rejected_duplicate` `:1363-1393`); STRONG-EMPIRICAL for the protocol (documented practice, not code).
- Epistemics risk: none; it strengthens "REFUTED is permanent unless the retry predicate is met".

### M2. A/A-null-derived decision band (KEEP / REJECT / INCONCLUSIVE)
- Mechanism: `contract_median_ci_verdict(null_ci95, claim_ci95)` in `fsqlite-e2e/benches/pipeline_stage_bench.rs:1262-1283`: `null_radius = max|A/A CI - 1|`; `min_gain = max(1 + 2·radius, 1.01)`, `max_regression = min(1 - 2·radius, 0.99)`; KEEP only if the *entire* claim CI clears the band; CV is provenance only. Bootstrap CI is a seeded LCG (`:923-946`, deterministic).
- Home: small-scale ladder "measured scaling" and the calibration gate for any empirical speedup claim before it becomes STRONG-EMPIRICAL.
- Cost: ~40 lines; needs an A/A arm per measurement.
- Evidence: PROVEN-in-source (`contract_tests :1545-1568`, including the 1% floor).
- Epistemics risk: none.

### M3. Anytime-valid e-process gates (Ville's inequality)
- Mechanism: self-contained Bernoulli simple-vs-simple LR martingale: `log E += log(alt_mult)` on a violation, `log((1-q)/(1-p0))` otherwise; alert at `E >= 1/alpha`; decision also requires `min_observations`, a clean streak, and deterministic audit sampling via `hash % stride` (`fsqlite-mvcc/src/ssi_eprocess_gate.rs:175-360`). Harness variant (`fsqlite-harness/src/eprocess.rs:1-130, 470-520`) wraps `asupersync::lab::oracle::eprocess::EProcess` with per-invariant (p0, lambda, alpha) calibration, an alpha budget by union bound, arithmetic-mean aggregation (valid under the intersection null regardless of dependence, `global_e_value`), and a `RejectionCertificate{e_value, threshold, observation_count, violations, rejection_time}`.
- Home: calibration layer (sequential evidence accumulation with no multiple-testing correction; the "strong-law-of-small-numbers" gate for toy-curve trials), and gate-layer drift monitoring of skill self-tests (`drift_monitor.rs:370-470` feeds parity mismatches per category and escalates Info/Warning/Critical).
- Cost: small; requires an honest p0 and exchangeable observations.
- Evidence: PROVEN-in-source for the self-contained gate (`ssi_eprocess_gate.rs` tests `:485-660`, incl. `supermartingale_under_null_stays_bounded :606-623`); STRONG-EMPIRICAL for the harness monitor (tests `:983-1740` read in part; core `EProcess` is in asupersync, unread).
- Epistemics risk: HIGH if copied as used. Here the gate exists to *skip* a correctness check (`connection.rs:64985-65010` runs FCW-only when the gate opens, `LAB_UNSAFE` only). Cairn must use e-processes only to accumulate/flag evidence, never to dissolve a gate. Also `observe_from_gate_report` (`drift_monitor.rs:392-412`) re-feeds static pass/fail counts every snapshot, violating exchangeability and inflating e-values.

### M4. Release certificate with evidence chain and verdict ordering
- Mechanism: `fsqlite-harness/src/release_certificate.rs:820-900` bundles gate decision, posterior bounds, drift state, adversarial counterexamples, CI flake budget, `evidence_chain: Vec<EvidenceChainEntry{source_bead, schema_version, content_hash(sha256), summary}>`, unresolved risks; `determine_verdict :1480-1535` applies hard rejects first (gate Fail, too many HIGH counterexamples, any drift rejection, missing artifact refs, failed fallback-transparency gate), then Conditional, then Approved. A no-mock critical-path gate (`no_mock_critical_path_gate.rs:1-60`) blocks mock-only evidence in critical categories.
- Home: gate layer (proportional-scrutiny router output) and claims DB (certificate = evidence pointer bundle).
- Cost: 6,325 lines here; Cairn needs only the verdict ordering + hashed evidence chain.
- Evidence: STRONG-EMPIRICAL (bodies read; tests not read).
- Epistemics risk: the upstream catalog self-declares `Verified` (see README-vs-code). Borrow the certificate shape only if every obligation carries an executed-evidence pointer and `Waived` never counts as satisfied.

### M5. History provenance + independent serializability oracle
- Mechanism: every transaction history carries `ScheduleProvenance{control: ObservationOnly|Deterministic, schedule_sha256, replay_command}` and the report records `deterministic_replay_claim` (`serializability_oracle.rs:50-80, 860-915`); observation-only runs "never claim deterministic schedule replay". Oracle builds a dependency graph, reports `Serializable | Inconclusive | Rejected` with a minimal witness and sha256 of history and report. Delta-debugging minimizer with content-addressed failure signatures (`mismatch_minimizer.rs:1-50`).
- Home: reproducibility gate (a claim must state whether it is replayable; observation-only evidence is labeled as such); Skeptic worker (minimize + dedupe counterexamples).
- Cost: the oracle is DB-specific; the provenance invariant is ~30 lines.
- Evidence: STRONG-EMPIRICAL (12 tests, `check_history` read; minimizer header only -> CONJECTURE).
- Epistemics risk: none.

### M6. Hash-chained, seekable commit marker stream
- Mechanism: fixed 88-byte LE records, `marker_id = BLAKE3("fsqlite:marker:v1" || commit_seq || time || capsule_oid || proof_oid || prev_marker_id)[..16]`, xxh3 per-record checksum, 1M markers/segment for O(1) seek, torn-tail detection, forged-record detection (`fsqlite-core/src/commit_marker.rs:1-120, 367-420`).
- Home: state layer append-only ledger / substrate lineage log.
- Cost: small, self-contained; dormant (native mode; consumers `epoch.rs`, `permeation_map.rs`, `native_index.rs`, not `Connection`).
- Evidence: STRONG-EMPIRICAL (25 `#[test]` in file, bodies not read).
- Epistemics risk: none. Contrast: `SsiEvidenceLedger` (`fsqlite-mvcc/src/ssi_abort_policy.rs:1263-1420`) is an in-memory bounded ring, and its `compute_chain_hash :1528-1572` concatenates variable-length lists without length prefixes (reframing collisions); do not copy that one.

### M7. Content addressing + three-tier hash policy
- Mechanism: `ObjectId = Trunc128(BLAKE3("fsqlite:ecs:v1" || canonical_header || payload_hash))` (`fsqlite-types/src/ecs.rs:14-100`); tiers: xxh3 = integrity, blake3 = content addressing, crc32c = protocol (`fsqlite-wal/src/checksum.rs:34, 1593-1598`).
- Home: substrate. Cost: trivial. Evidence: PROVEN-in-source (simple code + tier tests `:3054-3068`). Risk: 128-bit truncation is for non-adversarial data; Cairn should keep 256 bits.

### M8. Declarative, seeded fault-injecting VFS
- Mechanism: `FaultSpec{file_glob, kind: TornWrite{valid_bytes}|PowerCut|DiskFull|Latency{seeded jitter}|..., at_offset, after_nth_sync, max_triggers}`, replay seed, counter metric, trigger records (`fsqlite-harness/src/fault_vfs.rs:1-140, 440-496`).
- Home: skill self-tests / reproducibility gate for storage-touching Experimentalist skills.
- Cost: wrapper over a VFS trait; needs Cairn's own I/O seam.
- Evidence: STRONG-EMPIRICAL (18 tests in file; 5 consumers). The deterministic scheduler is `asupersync::lab::LabRuntime` (`fslab.rs:1-130`, 4 consumers) -> dependency-only. The loom test (`loom_page_lock_commit_ordering.rs:1-30`) and `cross_process_crash_harness.rs:1-10` are *models* of the engine, not the engine.

### Not accretive
- MVCC engine as a store (watchlist a/f): real but `>=10 writers unsupported`, UTF-8 only, CLI minimal, SQL fallbacks. Plain SQLite beats it for Cairn's state layer. Candidate home NONE.
- RaptorQ (b): codec is a dependency; sidecar/repair decision tree coded (`wal_fec.rs`, `checksum.rs:1077-1145`, `wal_fec_recovery.rs` 1,148 lines) but unwired. Nothing to borrow beyond "checksum mismatch -> repair only if surviving >= required and source hash verifies else truncate".
- Conformal martingale (`conformal_martingale.rs:1-207`: history-only median, sanitization tests only), `evalue_eviction.rs` (feature-gated decay heuristic), `conflict_model.rs` birthday model: homeless cleverness, CONJECTURE.
- `obligation.rs:1-60` linear-resource invariant (every Reserved obligation must reach Committed/Aborted; Leaked = bug, Lab mode panics) is a cheap protocol idea for the branch tree (no branch may be dropped without a terminal status), CONJECTURE.

**Verdict.** The most accretive thing is M1+M2 together: a negative-results ledger whose REJECTs are machine-gated (Blocked / RequiresNullControl), adjudicated into VALID/VOID classes, backed by a reachability proof and an A/A-null decision band. M3 is the cleanest small implementation of an anytime-valid gate here, to be borrowed as a calibration accumulator and never as a gate-skipper.

**Gotchas.** LICENSE is MIT with an OpenAI/Anthropic rider (`LICENSE:1-60`): no rights to Anthropic or anyone acting on its behalf, and "use" includes analyzing/indexing/ML pipelines; re-implement mechanisms from the math, do not copy code, and get legal review before any dependency. Rust nightly, edition 2024. The load-bearing statistics/scheduler/codec live in `asupersync` (unread). Chain hash without length prefixes (M6). Self-declared Verified obligations (M4). Non-exchangeable e-process feeding (M3). Markdown-heuristic ledger parser (M1).

**Sources.** README.md:20-80,174-215; docs/concurrency-contract.md:1-70; docs/LEDGER_RESURRECTION.md:1-130; docs/progress/perf-negative-results.md:1-135,1040-1120; Cargo.toml:48,150-230; LICENSE:1-80; fsqlite-mvcc/src/{ssi_eprocess_gate.rs:1-460,485-660; ssi_validation.rs:1-120,698-960; ssi_abort_policy.rs:1230-1420,1528-1572; conformal_martingale.rs:1-207; bocpd.rs:1-140; witness_objects.rs:1-130; invariants.rs:1-80,217-260; core_types.rs:1-150}; fsqlite-core/src/{connection.rs:2570-2600,64985-65010,71680-71700; commit_marker.rs:1-130,367-420; raptorq_codec.rs:1-80; wal_adapter.rs:1-60,640-700; wal_fec_adapter.rs:1-90; decode_proofs.rs:1-260}; fsqlite-types/src/{eprocess.rs:1-140; ecs.rs:1-120; obligation.rs:1-60}; fsqlite-wal/src/{wal_fec.rs:1-170; checksum.rs:1-90,1077-1170,1593-1598}; fsqlite-harness/src/{eprocess.rs:1-470,983-1745; drift_monitor.rs:1-120,360-470; replay_harness.rs:767-850; confidence_gates.rs:1-120; release_certificate.rs:1-110,820-900,1480-1535; parity_invariant_catalog.rs:1-200,770-800; verification_contract_enforcement.rs:1-70; fault_vfs.rs:1-140; fslab.rs:1-130; serializability_oracle.rs:1-80,840-960; mismatch_minimizer.rs:1-50; sql_pipeline_optimization.rs:733-797,845-960,1318-1438; no_mock_critical_path_gate.rs:1-60; score_engine.rs:1-80}; fsqlite-e2e/benches/pipeline_stage_bench.rs:915-960,1262-1290,1545-1575; fsqlite-mvcc/tests/loom_page_lock_commit_ordering.rs:1-70.
