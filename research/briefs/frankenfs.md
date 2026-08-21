## frankenfs v0.2.0 (@ 77b0a032b9f0)

**What it actually is.** A Rust workspace (21 crates + `tools/ffs-ops`, ~608K lines, `unsafe_code = "forbid"` at workspace level, Cargo.toml:43-44) implementing a userspace FUSE ext4/btrfs reader/writer with experimental layers: block MVCC (`ffs-mvcc`), a RaptorQ-based repair pipeline (`ffs-repair`), and an unusually large "evidence / release-gate" harness (`ffs-harness`, `tools/ffs-ops`). Files are monoliths (`crates/ffs-core/src/lib.rs` = 85,737 lines; `crates/ffs-block/src/lib.rs` = 14,353; `crates/ffs-repair/src/pipeline.rs` = 6,968). Testing is in-file `#[test]` modules plus integration tests, proptest, criterion benches, and libFuzzer targets; write paths (`create/mkdir/unlink/rename/write/symlink/setattr`, ffs-core lib.rs:30632-31223) exist, so RW compat is at least API-real, but none of that is a Cairn dependency candidate.

**README vs code**
- "RaptorQ self-healing (RFC 6330)" -> the codec is **not in this repo**: `codec.rs:21-26` imports `asupersync::raptorq::{decoder, gf256, rfc6330, systematic}`; no `raptorq` crate in any Cargo.toml; asupersync 0.3.4 is the sibling-project dependency (Cargo.toml:96). Decode is **erasure-only** and needs known corrupt indices (`codec.rs:390-433`; `recovery.rs:9` "V1 signal model: caller provides explicit corrupt block indices").
- "Proof over heuristic ... principled decision models rather than tuned constants" -> `decision.rs:77-117` is a hand-tuned 4x5 loss matrix with a hard 0.05 posterior threshold (`decision.rs:123`).
- "Bayesian Beta-posterior durability autopilot" -> real and wired: `autopilot.rs:133-143` (conjugate update), `332-367` (Beta-Binomial tail, correct log-space pmf recurrence), `226-260` (grid search over [0.03,0.10] step 0.001); invoked per scrub at `pipeline.rs:1552-1640`, clamped to layout capacity at `1585-1605`.
- "deterministic LabRuntime ... + DPOR" -> `LabRuntime` is asupersync's (`mvcc_stress_suite.rs:2,99`). The btrfs "DPOR" (`crash_consistency.rs:187-265`) is a linear crash-point enumerator along one observed flush order; `_dag` parameter unused; no partial-order reduction.
- "RaptorQ ... percentile stale-window SLO / four refresh policies" -> real (`pipeline.rs:58-81`, `160-262`, `1395-1440`); the scrub daemon itself is plain round-robin over groups with backpressure (`pipeline.rs:2110-2330`).
- **Watchlist (b) refuted**: zero matches for `e_value|e-value|evalue|e-process|conformal|martingale|betting|wealth|Ville` in any `.rs` under crates/tools/fuzz/tests/src. "anytime-valid" appears only as aspiration text (AGENTS.md:356; docs/archive/BRIDGE_PLAN_REALITY_CHECK_2026_05_20.md:103).
- **Watchlist (c)**: no content addressing, no Merkle tree, no CAS. blake3 is used for seed derivation (`symbol.rs:347-360`), PoR MACs (`por.rs:81-86`) and recovery verification; MVCC "dedup_identical" (`sharded.rs:372-586`) is identical-write elision.
- PoR header claims "l=460 of n=32768 -> <2^-128" (`por.rs:44-47`) contradicting its own `DEFAULT_CHALLENGE_COUNT = 8840` with derivation (`por.rs:62-69`); the constant is right. PoR and LRC are library-only (callers: `fuzz/fuzz_targets/fuzz_por_authenticator.rs`, `fuzz_lrc_repair.rs`, benches).
- `FaultInjector` "deterministic seed controls fault sequencing" -> seed is stored and echoed in the error string only (`ffs-block/src/lib.rs:6077-6092, 6164-6177`); rules are explicit per-block.
- README count guard is real and self-checking (`crates/ffs-harness/tests/readme_quantitative_claims.rs:8-140`).

### M1. Fail-closed claim-state evaluator (policy-as-data + monotone fold + provenance gating)
- **Mechanism**: `FeatureState` is a total order by `trust_rank` (Hidden 0 ... Validated 6; `release_gate.rs:39-76`). A JSON policy (`tests/release-gates/release_gate_policy_v1.json:1-90`) maps each public claim to required evidence lanes with `expected_outcome`, `missing_state`, `failed_state`, `skipped_state`, thresholds, and kill switches. `evaluate_feature` (`release_gate.rs:717-940`) starts at `target_state` and folds every finding with `more_conservative` (`1029-1036`); invalid or stale proof (git sha or timestamp, `proof_bundle.rs:912-958`) forces Disabled (`751-763`); a lane that *passed* but whose provenance class is DryRunHandoff / SmallHostSmoke / StaleArtifact / MissingRawLog / RedactionFailure "cannot strengthen public readiness" and downgrades (`proof_bundle.rs:2128-2240`; `release_gate.rs:795-822`; test `1315-1338`). Public wording is generated from the final state (`FeatureState::public_wording`, `release_gate.rs:78`), and a drift validator fails when docs claim a stronger state than controlling evidence (`docs_status_drift.rs:4-9`).
- **Home**: calibration layer / claims DB (claim tag must be <= what controlling evidence supports; stale evidence auto-downgrades; per-claim required lanes = scrutiny scaling).
- **Cost**: ~2k lines of schema + evaluator; a policy file to maintain.
- **Evidence**: STRONG-EMPIRICAL -- implementation read end-to-end; 29 `#[test]` in release_gate.rs, 56 in proof_bundle.rs (counted, three read at 1315-1400); not executed by me.
- **Epistemics risk**: none *if* the policy JSON lives in the immutable gate layer. If the orchestrator may edit it, this becomes a gate the strategy can dissolve.

### M2. ExecutedEvidence: executor-of-record evidence type
- **Mechanism**: `ExecutedEvidence` is `Serialize` but deliberately not `Deserialize`; the only constructor runs the process and records command, args, exit code, sha256(stdout), sha256(stderr), duration, `ran_at`, git sha, host class, and an outcome that separates Skipped(host-incapable) from Failed/Signaled/LaunchFailed (`executed_evidence.rs:1-8, 20-74, 169-226, 236-276`). Freshness = git sha equality AND age <= max (`278-321`). The proof-bundle validator re-runs each executable lane's declared command itself and requires a `pass` lane to hold green evidence at the expected SHA (`proof_bundle.rs:1955-1990`).
- **Home**: reproducibility gate / substrate node identity (command + git sha + output hashes ~ Cairn's (skill@version, inputs-by-hash, tool-versions)).
- **Cost**: low (~560 lines).
- **Evidence**: STRONG-EMPIRICAL -- body read; callers and tests exist at `evidence_backed_lane.rs:221-338`, `writeback_crash_matrix_executor.rs:272,403` (grep-located, bodies not read).
- **Epistemics risk**: none. Gotcha: forge-resistance is in-process only; serialized lanes are plain `Deserialize` JSON (`proof_bundle.rs:178-192`), no signatures.

### M3. Beta-posterior overhead autopilot (redundancy by expected loss)
- **Mechanism**: Beta(alpha,beta) over per-block corruption probability, conjugate-updated from each scrub (corrupt, checked) (`autopilot.rs:133-143`); `risk_bound(overhead, n)` = P(BetaBinomial(n,alpha,beta) > floor(n*overhead)) via log-space recurrence P(k+1)/P(k) = ((n-k)/(k+1)) * ((k+alpha)/(n-k-1+beta)) (`332-367`, verified correct); objective `storage_cost*overhead + loss_cost*risk` grid-searched over [min,max] (`177-260`); metadata groups get a loss multiplier (`325-329`).
- **Home**: substrate durability / retention policy (how much redundancy per artifact class, updated from audit observations).
- **Cost**: ~300 lines, O(n) per evaluation x ~70 candidates.
- **Evidence**: PROVEN-in-source for the math (I checked the recurrence and objective); tests listed at `autopilot.rs:743-887` by name (bodies not read), wiring at `pipeline.rs:1552-1640`.
- **Epistemics risk**: none.

### M4. Sampling-audit bound (PoR spot-check)
- **Mechanism**: `min_challenges(f, bits) = floor(bits*ln2 / ln(1/(1-f))) + 1` so that (1-f)^l < 2^-bits (`por.rs:510-527`); deterministic challenge set from a seed via BLAKE3 XOF with a visited-bitmap dedup (`211-266`); verifier rejects nonce mismatch, duplicate challenge indices, unchallenged extra responses, duplicate responses (`365-470`).
- **Home**: foundations auditor / reproducibility re-verification cadence (how many substrate nodes to re-check to bound undetected rot at fraction f).
- **Cost**: trivial.
- **Evidence**: PROVEN-in-source for the bound (simple algebra, read); protocol tests named at `por.rs:661-958` (bodies not read). Library-only in this repo.
- **Epistemics risk**: none. Note the (1-f)^l bound is with-replacement; dedup only tightens it.

### M5. README quantitative-claims guard with mutation self-test
- **Mechanism**: a test re-derives counts (git ls-files globs, enum-variant counts) and requires README to contain the derived strings and lack stale ones (`readme_quantitative_claims.rs:43-140`); a second test injects drift ("999 fuzz targets") and asserts detection (`24-41`).
- **Home**: claims DB / calibration layer ("every claim tagged"; docs cannot outrun code).
- **Cost**: trivial. **Evidence**: PROVEN-in-source (read; it is a test and proves it can fail). **Epistemics risk**: none.

### M6. Cross-oracle disagreement arbitration
- **Mechanism**: disagreement between oracles is never majority-voted; conflicting evidence is preserved with artifact hashes, classified (ModelBug / KernelBaselineIssue / ProductBug / HarnessBug / FixtureBug / UnsupportedScope / HostCapabilityGap / RepairOracleGap / InconclusiveConflict), ownership routed, and public claims fail closed while unresolved (`cross_oracle_arbitration.rs:3-8, 121-134`).
- **Home**: gate layer -- Skeptic vs Prover disagreement protocol ("convergence is not proof").
- **Cost**: low. **Evidence**: CONJECTURE -- header + enums read, 9 tests counted, validator body not read. **Epistemics risk**: none.

### M7. Fault-injection corpus with per-class confidence floors
- **Mechanism**: each row binds a deterministic seed, affected offsets, structure under attack, expected repair class (clean / partial / detection_only / false_positive / unsafe_to_repair) and a lower-bound confidence required before claiming that class; adversarial rows stay detection-only until calibration evidence upgrades them (`fault_injection_corpus.rs:3-15, 26-60`).
- **Home**: small-scale ladder / calibration layer (known-answer corpus with a required confidence per claim class).
- **Cost**: schema only. **Evidence**: CONJECTURE (header read). **Epistemics risk**: none.

### M8. RaptorQ group repair (dependency-only)
- **Mechanism**: per-block-group systematic encode, seed = blake3("ffs:repair:seed:v1"||uuid||group)[0..8] (`symbol.rs:347-360`), repair blocks in a group tail with dual descriptor slots and generation-publish ordering (`storage.rs:1-16`), erasure decode with direct path for <=2 erasures/<=64 sources (`codec.rs:37-38, 608`).
- **Home**: substrate durability -- but the codec is asupersync's, unverifiable here and license-encumbered; the borrowable part is M3.
- **Evidence**: STRONG-EMPIRICAL for the bridge (tests `codec.rs:1536-1580, 2589-2672`; fuzz `fuzz_repair_codec_roundtrip.rs`; fixtures `codec_corruption_fixtures.rs:1-70`). **Status**: dependency-only. **Epistemics risk**: none.

**Verdict.** One accretive thing: the fail-closed claim-state evaluator (M1) together with ExecutedEvidence (M2) -- a data-driven map from each public claim to required evidence, folded monotonically toward the most conservative state, with stale-evidence kill switches and provenance that stops a green-but-unauthoritative lane from strengthening a claim. M3/M4/M5 are small, correct, cheap borrows. Nothing here touches e-values or content addressing; the repair codec is a sibling-crate dependency, not a mechanism to re-implement.

**Gotchas**
- License is MIT **with an OpenAI/Anthropic rider** (LICENSE:1-40): no rights granted to Restricted Parties, and "use" includes indexing/evaluation pipelines. Re-implement mechanisms from description; do not vendor code.
- asupersync 0.3.4 (RaptorQ, LabRuntime, `Cx`) is threaded through every I/O signature; any code borrow drags the runtime.
- ExecutedEvidence is forge-resistant only in-process; no signing.
- Wall-clock `now_ns` in evidence (`evidence.rs:39-45`); evidence ledger is plain JSONL with no hash chain (`evidence.rs:442-510`).
- "DPOR" and "deterministic seed" wording overstate the code.
- Monolith files; heavy agent-swarm provenance (bead ids in every doc comment).

**Sources**: Cargo.toml:1-140; README.md:1-120; crates/ffs-repair/src/{codec.rs:1-140,333-572,1536-1580,2589-2672; symbol.rs:1-110,270-362; decision.rs:1-230; autopilot.rs:1-412; scrub.rs:1-90,204-330; pipeline.rs:40-120,199-262,1237-1360,1395-1440,1552-1640,2110-2330; por.rs:1-110,185-300,365-530; lrc.rs:1-50; evidence.rs:1-70,442-550; storage.rs:1-60; recovery.rs:1-60,140-175}; crates/ffs-repair/tests/codec_corruption_fixtures.rs:1-70; fuzz/fuzz_targets/fuzz_repair_codec_roundtrip.rs:1-80; crates/ffs-block/src/lib.rs:6016-6260; crates/ffs-harness/src/{release_gate.rs:1-80,717-940,1024-1040,1315-1400; proof_bundle.rs:1-60,162-260,362-436,567-590,880-960,2128-2250,1940-1990; executed_evidence.rs:1-110,169-330; docs_status_drift.rs:1-70; support_state_accounting.rs:1-60; cross_oracle_arbitration.rs:1-140; fault_injection_corpus.rs:1-60}; crates/ffs-harness/tests/readme_quantitative_claims.rs:1-140; tests/release-gates/release_gate_policy_v1.json:1-90; crates/ffs-mvcc/src/lib.rs:956-1020,1095-1150; crates/ffs-mvcc/tests/mvcc_stress_suite.rs:92-160; crates/ffs-btrfs/src/crash_consistency.rs:1-50,187-265; FEATURE_PARITY.md:1-60; LICENSE:1-40; AGENTS.md:356; docs/archive/BRIDGE_PLAN_REALITY_CHECK_2026_05_20.md:95-110.
