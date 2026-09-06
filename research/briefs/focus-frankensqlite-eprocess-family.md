# Focus read: frankensqlite e-process / conformal-martingale / statistical-gate family

Repo: `/private/tmp/claude-502/-Users-jwross-Documents-cairn/9cf1d827-93dc-467a-8101-c39c1c16857b/scratchpad/repos/frankensqlite` (v0.3.7 @ 9b1d3ed7b3cbb03675a8eeeb136099cecdf6ed0a). All paths below are relative to that root unless absolute. Line numbers are from the files as printed during this read.

Method: read every file in the family end to end (except `crates/fsqlite-types/src/eprocess.rs`, already read by the requester; cross-references only), read the external primitive it wraps (`asupersync/src/lab/oracle/eprocess.rs`, sibling clone in `scratchpad/repos/asupersync`), and grepped every symbol for callers outside its own file to separate load-bearing code from library surface that nothing calls.

## Summary table

| File | Mechanism | Math status | Status | Cairn home | Tag |
|---|---|---|---|---|---|
| fsqlite-types/eprocess.rs | fixed-λ Bernoulli betting supermartingale (query shedding) | valid (requester verified) | real | primitive only | (requester's call) |
| mvcc/conformal_martingale.rs | windowed conformal p-value + linear betting f(p)=1+λ(0.5−p), reset on hit | approximately valid; windowed p-values not conditionally uniform; doc over-claims Ville | vestigial (no callers) | NONE | CONJECTURE |
| mvcc/regime_monitor.rs | enum dispatch BOCPD vs conformal martingale | n/a | vestigial | NONE | n/a |
| mvcc/ssi_eprocess_gate.rs | simple-vs-simple Bernoulli LR e-process + Clear/Watching/Alert state machine + clean-streak + deterministic audit sampling; gates skipping SSI validation | e-process correct; the skip inference is inverted (absence of alert ≠ bounded miss rate) | real, LAB_UNSAFE only | SKILL SELF-TESTS / SELECTOR AUDIT (state machine + audit sampling only) | STRONG-EMPIRICAL (state machine); SPECULATION (safety claim) |
| mvcc/sheaf_conformal.rs | pairwise section-compatibility check ("sheaf"), split-conformal per-invariant threshold, impact·confidence/effort score | conformal quantile correct; OpportunityScore is not statistics | partial (e2e harness test only) | CALIBRATION LAYER / SMALL-SCALE LADDER (split-conformal threshold) | PROVEN-in-source (quantile); SPECULATION (OpportunityScore) |
| pager/evalue_eviction.rs | per-page e ← e·1.5 on access, e·0.95 per tick, argmin victim, "Ville p-value" = 1/e | not a supermartingale under its own stated null; decayed access counter mislabeled | vestigial (feature-gated, never consulted for real eviction) | NONE | SPECULATION |
| harness/eprocess.rs | wraps asupersync EProcess; per-invariant calibration; log-grid λ mixture; arithmetic-mean global e-value; rejection certificate + evidence ledger | correct (mixture and mean are valid e-processes) | partial/vestigial (tests only) | GATE LAYER (evidence-ledger shape; e-value aggregation) | PROVEN-in-source (primitive + aggregation) |
| harness/confidence_gates.rs | obligation counts → Pass/Conditional/Fail/Waived; Beta posterior per category; weighted lower bound vs floor; expected-loss ranking; fail-closed config | Beta math fine; "mismatch probability" is a shrunk completion fraction; "conformal" in title is a misnomer here | real (release certificate / adversarial search / CI bins) | GATE LAYER (fail-closed + waiver-explicit + downgrade-only override) | STRONG-EMPIRICAL |
| harness/verification_gates.rs | declarative command plan, expected exit codes, ordered scopes, block-and-skip, JSON report | none (mechanical) | real (CI bins) | GATE LAYER | PROVEN-in-source |
| harness/ratchet_policy.rs | persisted high-water mark on lower bound, Allow/Block/Quarantine/Waiver, non-waivable floor, expiring waivers, rollback signal | none beyond comparisons; semantics correct | partial (complete + tested; evaluate_ratchet called only from a test) | CALIBRATION LAYER / SELECTOR AUDIT (tag ratchet) | STRONG-EMPIRICAL |
| harness/drift_monitor.rs | per-category Bernoulli e-process + EMA "BOCPD" + alarm levels + runbooks | update rule fine; the wired feed is a static snapshot (order-dependent, vacuous in release path) | real (wired) but feed broken | SELECTOR AUDIT (alarm/runbook shape only, on a genuine stream) | CONJECTURE |

---

## 0. `crates/fsqlite-types/src/eprocess.rs` (cross-references only)

Not re-read. Consumers: `crates/fsqlite-types/src/cx.rs:172` imports `EProcessDecision, EProcessOracle, EProcessSnapshot`; `cx.rs:487-488` holds the oracle; `cx.rs:1432` `set_eprocess_oracle`; `cx.rs:1562-1568` consumes `decision.should_shed` and logs `eprocess_shedding_triggered`; tests at `cx.rs:2507-2535`. The same fixed-λ Bernoulli primitive appears again in `asupersync/src/lab/oracle/eprocess.rs:224-257` (factor `1 + λ(x − p0)` clamped to ≥ 1e-15, capped at `max_evalue`, sticky `rejected`) and a third time inline in `harness/drift_monitor.rs:219-236`. So the repo has three copies of one primitive.

---

## 1. `crates/fsqlite-mvcc/src/conformal_martingale.rs` (207 lines)

**Mechanism.** `observe(x)` (82-142): maintains a `VecDeque` history of at most `window_size` values (default 100, 28) and an incremental regime mean (87-88). Until `min(window_size, 10)` points exist it only records (90-98). Then: nonconformity score = `|x − median(history)|` with the median taken over history only (102-106); conformal p-value = `(1 + #{h ∈ history : |h − median| ≥ score}) / (n + 1)` (108-116); betting factor `f(p) = 1 + λ(0.5 − p)` (119-123); `wealth *= max(f, 0.01)` (124); threshold `1/α` (127); on crossing: flag change point, reset wealth to 1, regime mean to x, clear history (128-136). Defaults α = 0.05, λ = 0.5 (25-33); `sanitize` forces λ ∈ (0,2), α ∈ (0,1), window ≥ 1 (35-56).

**Math.** Nonnegativity: `f ≥ 1 − λ/2 > 0` for λ < 2, so the max(·, 0.01) clamp is inert at default λ and only activates for λ > 1.98, where it inflates the factor and breaks `E[f] ≤ 1` (latent, not reachable with defaults). Per-step validity: if p is uniform, `E[f] = 1`; if p is conservative (ties counted with `>=` plus the +1 for x itself make it super-uniform), `E[p] ≥ 0.5` so `E[f] ≤ 1` for λ > 0. Two real caveats: (a) the median is computed on history excluding x while each h is scored against a median that includes h, so the score is not a symmetric function of the augmented bag and the p-value is only approximately valid; (b) each p_t is computed against a sliding window that overlaps the previous window, so successive p-values are not conditionally uniform given the past, and the product is not a test martingale in Vovk's sense (conformal test martingales use all prior observations). The module docstring's "finite-sample guarantees via Ville's Inequality" (1-5) is over-claimed; the hedge at 7-11 only addresses non-stationarity, not the window dependence. Reset-on-detection (130-135) is restart semantics and does not break per-segment validity. Nothing is averaged or rescaled mid-run.

**Decision.** `change_point_detected()` flag and `current_regime_stats()` (144-153). What consumes it: nothing. `RegimeMonitor` wraps it (regime_monitor.rs:6-7, 23-26) and `lib.rs:457` re-exports it; the repo-wide grep for `ConformalMartingaleMonitor::new|RegimeMonitor::|RegimeMonitorConfig` outside these two files and `bocpd.rs` returns only the `lib.rs` re-exports.

**Tests.** 168-206: config sanitizing and no-panic on window 0. No test touches the p-value, the betting factor, or false-alarm rate; a broken update (e.g. `1 + λ(p − 0.5)`) would pass.

**Status.** Vestigial.

**Cairn.** Home NONE as implemented. Conceptually, conformal p-values against a growing baseline are a legitimate way to ask "is this measurement anomalous relative to prior runs," but the split-conformal threshold in sheaf_conformal.rs (below) does that more cleanly. Tag CONJECTURE. Epistemics risk: low (it only sets a flag).

---

## 2. `crates/fsqlite-mvcc/src/regime_monitor.rs` (65 lines)

**Mechanism.** Enum dispatch: `RegimeMonitorConfig::{Bocpd, ConformalMartingale}` (10-13), default ConformalMartingale with the comment "superior distribution-free properties and performance" (15-21); `observe`/`change_point_detected` delegate (38-50). `bocpd.rs` (out of scope, inspected for context) is a genuine run-length-posterior BOCPD (`bocpd.rs:4, 15, 376-379, 435, 466`).

**Status.** Vestigial; only `lib.rs:554` re-exports it. No math. Home NONE.

---

## 3. `crates/fsqlite-mvcc/src/ssi_eprocess_gate.rs` (702 lines)

**Mechanism.** Config (89-127): α = 1e-3, p0 = 1e-4, alt_mult = 50 (so q = alt_mult·p0 = 5e-3), `min_observations` 64, `min_clean_streak` 32, `periodic_sample_rate` 0.05. `new` clamps invalid values and clamps alt_mult into [2, 1/p0 − 1] (209-233); caches `log_lr_one = ln(alt_mult)` and `log_lr_zero = ln((1 − q)/(1 − p0))` (231-233). `observe(conflict)` (256-281): `log_e += log_lr_one` on conflict (and `clean_streak = 0`), `+= log_lr_zero` on clean (`clean_streak += 1`); tracks peak and alert transitions. `alert_state()` (285-296): Clear until `min_observations`; Alert iff `log_e ≥ ln(1/α)`; Watching iff `log_e > 0`. `should_skip_ssi(hash)` (312-347): false if Alert, or obs < min, or streak < min_clean; then deterministic audit sampling: stride = round(1/rate), force full validation when `hash % stride == 0`; else grant. `reset()` (352-360) is manual only.

**Math.** The likelihood ratio is exactly right: `E[LR | rate = p0] = p0·(q/p0) + (1 − p0)·(1 − q)/(1 − p0) = q + 1 − q = 1`, so the product is a martingale at p0 and a supermartingale for any rate ≤ p0; log-domain keeps it nonnegative; nothing averages or rescales it; Ville applies to the Alert event. So: `P(ever Alert | true rate ≤ p0) ≤ α` is a correct statement.

Where it goes wrong is the inference drawn from it. The docstring (59-70) says "the e-process bounds the long-run rate at which we incorrectly skip a commit that did have a pivot by α." It does not. Ville bounds the false-alarm probability of the *reject* decision. The *skip* decision is taken when H0 is **not** rejected, and nothing about a non-rejection is α-controlled: under H0 exactly, each skipped commit still carries a pivot with probability p0 = 1e-4 regardless of α; under a true rate anywhere between p0 and q the e-process can sit below threshold indefinitely. Also, under H0 `log_e` drifts down by `|log_lr_zero| ≈ 0.0049` per clean observation, so after ~10 000 clean commits `log_e ≈ −49` and roughly `(49 + 6.9)/3.9 ≈ 14` consecutive conflicts are needed to alert; there is no restart-at-1 or CUSUM-style e-detector, so regime-change detection is slow and the `min_clean_streak = 32` heuristic is what actually closes the gate quickly (a single conflict zeroes the streak, 264-266). The docstring's "resetting the e-process whenever the caller observes a conflict" (67-68) is not implemented: `observe` resets only the streak, and `reset_ssi_e_process_gate` (connection.rs:71717) has no caller in connection.rs.

**Decision / wiring.** Production code behind `PRAGMA fsqlite.write_merge = LAB_UNSAFE` (connection.rs:2570-2590; `should_skip_ssi_validation` returns false under Safe, 71688-71695). Commit path: `connection.rs:64993-65011` computes `audit_hash = session_id ^ planned_commit_seq`, consults the gate, and picks `prepare_concurrent_commit_fcw_only` (skip) vs `prepare_concurrent_commit_with_ssi`. Observations are fed only when full validation ran (`connection.rs:65141-65157`), which is the right thing. α is PRAGMA-settable (69320-69345). `begin_concurrent.rs:3270-3290` documents the FCW-only fast path.

**Tests.** Unit 484-701: state machine (open after clean history 513-521; conflict closes 524-533; min_observations 536-547; alert on burst 550-568; reset 571-586; audit stride 589-603; config clamping 494-510). `supermartingale_under_null_stays_bounded` (606-623) feeds only zeros and asserts e ≤ 1, which only checks the sign of `log_lr_zero`; a wrong `LR(1)` (say 2·alt_mult) passes every test. Integration: `crates/fsqlite-core/tests/ssi_e_process_gate.rs` (11 tests, 51-273) and `ssi_e_process_wired.rs` (50, 115, 186; the 186-235 test drives the gate to Alert via the API and checks no skips are granted on the live commit path).

**Status.** Real, lab-gated, actively wired.

**Cairn.** The reusable part is not the statistics but the gate state machine: `Clear/Watching/Alert`, a cold-start minimum, a clean-streak requirement, and above all **deterministic audit sampling that keeps feeding the monitor even when the fast path is taken** (325-343). That shape fits SKILL SELF-TESTS ("a skill's cached/fast answer may be trusted only while sampled known-answer re-runs keep passing") and the SELECTOR AUDIT. Cost: ~150 lines. Tag STRONG-EMPIRICAL for the state machine (integration-tested on the live commit path). The "skip is safe because nothing alerted" inference is the epistemics hazard and must not be borrowed: a calibration layer that let "no e-process alarm" promote a claim would be making exactly this mistake.

---

## 4. `crates/fsqlite-mvcc/src/sheaf_conformal.rs` (734 lines)

**Mechanism.** "Sheaf" here means: each transaction is a `Section` = map page → observed version (18-23); `check_sheaf_consistency` (75-135) compares every pair of sections; on the pages they share, the pair is consistent if A's versions are all ≤ B's or all ≥ (under the supplied order, or equality if none); an obstruction is recorded per disagreeing page when neither direction holds (108-127). `check_sheaf_consistency_with_chains` (150-222) does the same using position in an explicit per-page version chain, and treats unknown versions as obstructions (189-197). It is a pairwise compatibility (no "zig-zag" reads) check, O(n²·pages); no higher cohomology or gluing. The conformal calibrator (230-385) is textbook split conformal: calibrate by appending scores per invariant (307-315); threshold = the `ceil((1 − α)(n + 1))`-th order statistic (362-384: `q_idx = ceil((1−α)(n+1))`, `idx = min(q_idx, n) − 1`); conforming iff `score ≤ threshold` (346); unknown invariant → +∞ (369-371); `min_calibration_samples` 50 (241). `OpportunityScore = impact·confidence/effort`, pass iff ≥ 2.0 (397-421).

**Math.** The quantile index is the standard one and correct (n = 100, α = 0.05 → 96th smallest). Marginal coverage ≥ 1 − α holds under exchangeability of calibration and test scores. There is no p-value, e-value, or anytime claim, so nothing to break; one operational caveat is that the calibration pool grows without bound (307-315), so online use mixes regimes. `OpportunityScore` has no statistical content: "confidence" is a typed-in number (399-400). `perf_loop.rs` does not use it (it defines its own `OPPORTUNITY_SCORE_THRESHOLD = 2.0` at perf_loop.rs:57).

**Decision.** Library; consumed only by `crates/fsqlite-harness/tests/e2e_sheaf_plus_conformal_mvcc_verification.rs:7-8, 127-197` (calibrate on consistent sections across seeds, flag an injected inconsistency). Not on any production path.

**Tests.** 447-733. Sheaf: disjoint/agree/disagree/ordered/chain/unknown (448-579). Conformal: min-samples (582-599), gross anomaly (602-646, would catch an inverted quantile), coverage ≥ 0.90 on a deterministic holdout (649-690, loose enough that an off-by-one index passes). OpportunityScore boundary (693-733).

**Status.** Partial (correct library, e2e-tested, not wired).

**Cairn.** Home: CALIBRATION LAYER / SMALL-SCALE LADDER. The split-conformal threshold is the cheap, distribution-free answer to "is this new measurement anomalous relative to the ladder baseline" (e.g. per-skill known-answer cost profile drift, or a 60-bit residual against the 30/40/50-bit scaling fit). ~40 lines to re-implement. Tag PROVEN-in-source for the quantile (verified and tested, though tests are loose). Do not borrow OpportunityScore: a number that looks quantitative but encodes a subjective "confidence" is precisely what blurs a calibration boundary.

---

## 5. `crates/fsqlite-pager/src/evalue_eviction.rs` (720 lines)

**Mechanism.** Per page an `AtomicF64` e-value (109-144). `record_access`: `e ← clamp(e·r_hit)`, new pages start at `initial_e·r_hit` (242-258); `tick`: every page `e ← clamp(e·r_tick)` (265-270), `tick_n` (274-283); defaults `r_hit = 1.5`, `r_tick = 0.95`, `initial_e = 1` (85-97); clamp to [1e-30, 1e30] (101-104, 330-335); `choose_victim = argmin e`, untracked = 1 (301-312); `ville_pvalue = min(1, 1/e)` (319-325). The page cache ticks every 1024 accesses (page_cache.rs:2896-2905).

**Math.** Not a supermartingale under any null the module states. Take one tick period with null access probability p: `E[factor] = r_tick·(1 + p·(r_hit − 1)) = 0.95·(1 + 0.5p)`, which is ≤ 1 only for p ≤ 0.105; the docstring's own null "access rate 1/3" (82-84) gives 1.108 > 1. The claim at 89-91 that a page accessed every third tick has expected e exactly 1 is false: `1.5·0.95³ = 1.286`. Worse, the number of accesses between ticks is unbounded (1024 accesses per tick), each multiplying by 1.5, so there is no per-step normalization at all. "Bayesian mixture," "Robbins mixture," "Kelly-optimal" (38-48, 82-84) are decorative: `r_hit` is a constant, nothing is integrated. The docstring at 24-29 and `ville_pvalue` read `1/e` as "the probability of that page being a true positive (hot)," a posterior misreading even for a valid e-process. Clamping at the floor inflates (negligible). What the code actually computes: `log e = (#accesses)·ln 1.5 + (#ticks)·ln 0.95`, an exponentially aged access counter — a perfectly reasonable LFU-with-decay heuristic wearing e-process vocabulary.

**Decision / wiring.** Behind cargo feature `evalue-eviction` (73; `crates/fsqlite-pager/Cargo.toml:25`). `page_cache.rs` owns one (2621, 2767), records accesses (2897), and exposes `evalue_choose_victim`/`evalue_ville_pvalue` (2911-2935), but the real eviction decision goes through the policy tracker (`page_cache.rs:795-800, 1112`); repo-wide grep finds no caller of `evalue_choose_victim` or `evalue_ville_pvalue` outside page_cache.rs.

**Tests.** 352-719 pin arithmetic (growth, decay, clamp, concurrency, argmin). `hot_page_grows_as_r_hit_pow_t` (387-416) asserts a page accessed every tick at r_hit·r_tick = 1 "sits at null boundary … This IS the intended martingale property," which encodes the misunderstanding (a page accessed every tick is maximally hot). No test checks `E[factor] ≤ 1` under any null.

**Status.** Vestigial/advisory.

**Cairn.** Home NONE. Tag SPECULATION. Epistemics risk: this is the cleanest specimen in the repo of a heuristic score presented with Ville/p-value language; it is the pattern Cairn's calibration layer exists to forbid.

---

## 6. `crates/fsqlite-harness/src/eprocess.rs` (2094 lines)

**Mechanism.** Wraps `asupersync::lab::oracle::eprocess::EProcess` (28): factor `1 + λ(x − p0)` clamped ≥ 1e-15, capped at `max_evalue`, sticky `rejected` with `rejection_time` (asupersync eprocess.rs:224-257); `validate` enforces λ ∈ (−1/(1−p0), 1/p0), α ∈ (0,1], `max_evalue ≥ 1/α` (112-158). Per-invariant calibration (99-130): hard/CAS invariants p0 = 1e-9, λ = 0.999, α = 1e-6; software invariants p0 = 1e-6, λ = 0.9, α = 1e-3; SSI false-positive rate p0 = 0.05, λ = 0.8, α = 0.01. `MixtureEProcess` (496-599): uniform weights over a log-grid of λ in [0.01/p0, 0.95/p0] (509-527), `e_mix = Σ w_j E_j` via log-sum-exp (558-580), reject at 1/α (584-586). `MvccEProcessMonitor` (610-869): one process per invariant, global e-value = arithmetic mean (725-731), `global_rejected` at 1/α_global (735-737), `any_rejected` (741-743), `RejectionCertificate` (420-435, 768-781), `AggregatedEvidenceEntry` with per-contributor weighted evidence and share (462-486, 822-868), structured tracing at checkpoint/warn/reject (666-710). `RuntimeInvariantMonitor` (339-399): hard invariants INV-1..7 checked by `debug_assert!` predicates (247-336), e-process only for the SSI-FP rate; `uses_eprocess_for` returns true only for SSI-FP (355-357). Lock-exclusivity observer (181-230).

**Math.** Correct. Mixture of supermartingales with fixed convex weights is a supermartingale; arithmetic mean of e-values is an e-value under the intersection null regardless of dependence (docstring 20-24, 720-723, accurately stated). The cap shrinks, so validity holds; the ≥ 1e-15 clamp cannot fire with a validated λ. One calibration observation: for a must-never-happen invariant, factor ≈ 2 per violation means ~20 violations before reaching 1e6 (the test at 1305-1306 computes 11 for α = 1e-3) — the module itself sidesteps this by asserting hard invariants deterministically and reserving the e-process for a genuinely stochastic rate (338, 1971-1984). That separation is the right one.

**Decision.** Test-harness library. Repo-wide grep finds no caller of `MvccEProcessMonitor|RuntimeInvariantMonitor|MixtureEProcess|create_mvcc_monitors|observe_lock_exclusivity|check_hard_invariants` outside this file; `parity_invariant_catalog.rs:1193, 1933-1973` reference function names as strings, `fault_profiles.rs:30` imports only the `MvccInvariant` enum. The CI gate `phase6.eprocess_inv` (verification_gates.rs:1063-1077) runs `test_eprocess_inv1_through_inv7`, which (2090-2093) calls the 100-thread hard-invariant stress test, not an e-process test.

**Tests.** 881-2094. `test_eprocess_single_violation_jumps` (955-978) pins the x = 1 factor to 1e-6 — this would catch a broken violation factor. The "stays near one" tests (928-950, 1101-1113) allow (0.5, 2) after 10k clean steps, so a wrong x = 0 factor passes. `test_eprocess_supermartingale_empirical` (1744-1781) draws 200×500 Bernoulli(1e-6) observations (≈ 0.1 expected violations in total) and asserts mean < 2 — near-vacuous. The "no false alarm under null" tests (1161-1186, 1722-1739) feed zero violations, which is not the null. Mixture power and non-rejection-under-zeros (1018-1072). Certificate and ledger shape (1232-1257, 1784-1831). Runtime monitor SSI-FP power and optional-stopping checkpoints (1915-2040; note 1987-2007 feeds exactly 5% = p0 deterministically and asserts no rejection at five stop points — that is a real H0 check, though deterministic).

**Status.** Partial/vestigial (exercised only by its own tests).

**Cairn.** Home: GATE LAYER (and SELECTOR AUDIT reporting). Two things are worth copying: (1) the evidence-ledger shape — a rejection certificate carrying e-value, threshold, observation count, empirical rate, rejection time, plus an aggregated entry listing which monitors contributed what share (462-486) — as the provenance record for "why did this gate fire"; (2) the rule that a set of independent monitors is combined by arithmetic mean (or a mixture over λ) rather than by max or product. Cost: ~200 lines. Tag PROVEN-in-source for primitive + aggregation (math verified; x = 1 factor tested). Epistemics risk: low for the math; the lesson to carry over is the file's own: deterministic invariants get asserted, only rates get e-processes.

---

## 7. `crates/fsqlite-harness/src/confidence_gates.rs` (1421 lines)

**Mechanism.** Per invariant: count Verified/Pending/Partial/Waived obligations → `GateDecision` Pass (all satisfied) / Waived (all waived, if policy allows) / Conditional (some verified or partial) / Fail (303-355). Per category: passing/total, Beta(prior.α + passing, prior.β + failing) posterior mean and equal-tailed credible interval (358-418; `score_engine.rs:129-133`, quantile by bisection on the regularized incomplete beta, 259-281); decision Pass at 100%, Conditional ≥ `category_min_verification_pct` (50), else Fail (396-404). Global: weighted posterior mean and weighted lower bound using category weights (456-468); `release_ready` iff config valid ∧ all categories pass ∧ weighted lower bound ≥ `release_threshold` (470-484); `release_threshold` must be ≥ `STATISTICAL_RELEASE_FLOOR = 0.70` (`score_engine.rs:52`; 92-100) and invalid configs fail closed (474-475). Expected-loss ranking: `(1 − posterior mean) × category weight × loss_asymmetry` (620-728), sorted deterministically. Evidence ledger (747-841). `apply_contract_outcome_to_gate_report` lets contract enforcement set the final decision (514-536).

**Math.** Beta posterior and interval are standard and implemented sanely. The modeling is the issue: obligation statuses are treated as Bernoulli draws from a "pass rate," so `mismatch_probability` (701-728) is `1 − (shrunk fraction verified)`, a completion percentage with a prior, not a probability that an invariant is violated. The weighted sum of per-category lower bounds (464-468) is a heuristic, not a joint bound. The title's "conformal confidence gates" (1-5) is a misnomer for this file — no conformal band is computed here (ratchet_policy.rs:379 reads `scorecard.conformal_band.lower` from `score_engine`, not from here).

**Decision.** CI/release gate, load-bearing: `release_certificate.rs:1552-1553` evaluates it and 1488-1490 rejects the certificate on global Fail; `adversarial_search.rs:347-705` mutates catalogs and checks gate monotonicity; bins `parity_verification_workflow_runner.rs`. `GateConfig` is embedded in `certification_policy.rs:13, 140, 173-178`.

**Tests.** 847-1421: structural (counts, ranges, ordering, JSON round trip), and the valuable ones: fail-closed for threshold below floor (1317-1327), NaN/∞/invalid prior/invalid confidence → Fail without panic (1330-1381), a serialized config missing `waived_obligations_satisfy_gate` must not deserialize (1015-1029), contract outcome can block (1032-1050). They would catch a regression in fail-closed behavior; they do not test interval numerics (score_engine.rs:796-814 has three quantile sanity tests).

**Status.** Real.

**Cairn.** Home: GATE LAYER. Borrow the policy skeleton, not the posterior: (a) four-state decision with Waived distinct from Pass and `is_pass()` explicit about which states count (127-133); (b) the waiver policy flag is part of the serialized config and its absence is a deserialization error (1015-1029); (c) invalid configuration yields Fail, never Pass (474-475); (d) an external enforcement result can only move the final decision to Fail or confirm Pass, with the rationale appended (514-536). Cost: ~150 lines. Tag STRONG-EMPIRICAL. Epistemics risk: if Cairn borrows the Beta "mismatch probability," it must be labeled a prioritization heuristic and never allowed to move a claim's calibration tag.

---

## 8. `crates/fsqlite-harness/src/verification_gates.rs` (2187 lines)

**Mechanism.** A static list of `GateSpec { gate_id, gate_name, scope, command, env, expected_exit_code }` (574-582; plans 585-1350): universal gates are `cargo check/clippy/fmt/test/doc`, an undocumented-`#[ignore]` scan, `rg` for unsafe with **expected exit 1** (647-669), beads dependency-cycle and sync checks, spec audits (587-755); phase 2..9 gates each run one named test or binary (757-1334; e.g. `phase4.sql_conformance_20`, `phase5.wal_crash_recovery`, `phase6.ssi_write_skew`, `phase9.no_regression` which runs `bd_mblr_7_3_2_regression_detector`, 1319-1333). Runner: `run_scope` executes all gates of a scope and returns all-pass (1367-1383); phase runners execute scopes in order and, on failure, push every later-scope gate as `Skipped` with a `blocked_by_*` reason (279-354, 358-433, 437-512, 1385-1407); `execute_gate` compares exit code to expected, captures stdout/stderr/duration (1409-1450); reports serialize to JSON (63-134, 519-572). `GateCommandRunner` trait allows a mock (145-156).

**Math.** None.

**Decision.** CI gate runners: `bin/phase_1_3_gate_runner.rs:5`, `phase_4_6_gate_runner.rs:5`, `phase_7_9_gate_runner.rs:5`, and harness compliance tests (`tests/bd_331_*`).

**Tests.** 1462-1967 with `MockRunner` (1473-1475): plan contents per gate and the blocking semantics (1774-1810 asserts universal failure marks every phase-2/3 gate Skipped; 1811, 1906, 1943 likewise for later phases). A broken block-and-skip rule would be caught.

**Status.** Real.

**Cairn.** Home: GATE LAYER — this file is close to a literal specification of "mechanical, immutable checks": a declarative plan, expected exit codes (including expected-failure greps), ordered scopes where an earlier failure blocks and records the block reason, and a machine-readable report that keeps the raw output. Cost: ~300 lines of Rust, or less in Python. Tag PROVEN-in-source. Epistemics risk: none; it is the non-statistical layer.

---

## 9. `crates/fsqlite-harness/src/ratchet_policy.rs` (1320 lines)

**Mechanism.** `RatchetPolicy` (51-78): `regression_tolerance` (default 0.0), `category_regression_tolerance` (0.005), quarantine enable/max (5), waivers enable, `minimum_release_threshold = STATISTICAL_RELEASE_FLOOR` (80-91); `strict()` disables quarantine and waivers (96-105). `RatchetState` (127-154) persists the global high-water mark (HWM) of the lower bound, point-estimate HWM, per-category HWMs, evaluation count, quarantine streak/reason, active waiver, and a 50-entry history ring (157). `evaluate_ratchet` (371-549): candidate lower bound, regression = HWM − candidate (377-382); `metrics_are_valid` demands finite in-range values, non-empty categories, every persisted category present in the candidate, and a release threshold ≥ floor (383-405); `meets_threshold` requires candidate ≥ policy floor, ≥ scorecard threshold, and conformal lower ≥ threshold (406-409); per-category regressions beyond tolerance (411-434); verdict order: Block if `!meets_threshold` (non-waivable, 437-440) → Allow if regression ≤ tolerance and no category regressed (441-443) → Waiver if one is active, enabled and unexpired (444-447) → Quarantine on request or active streak < max (448-467) → Block. State update: only Allow advances HWMs and clears quarantine (483-504); Quarantine increments streak (505-510); history ring trimmed (517-528); expired waivers dropped (530-535). `check_rollback_signal` (604-648): Block ∧ (regression > 2·tolerance + 0.01 ∨ three consecutive Blocks).

**Math.** Comparisons only, truncated to 6 decimals for determinism (`truncate_score`, parity_taxonomy.rs:292-294). Semantics are a correct monotone ratchet: the HWM never decreases; Quarantine/Waiver let a regression through without moving the HWM, so the debt remains; the floor cannot be bypassed by either.

**Decision.** `RatchetPolicy::strict()` is embedded in `certification_policy.rs:184-186` (and `GateConfig` at 173-178), but `evaluate_ratchet` is invoked only from `tests/bd_1dp9_6_6_alien_contract_pack_enforcement.rs:392` (repo-wide grep for `evaluate_ratchet(|ratchet_state.json|check_rollback_signal(` outside the module). No bin or release path runs the ratchet.

**Tests.** 715-1320, thorough: seed below floor blocks (761-769), allow on same/improved (774-797), strict block and tolerance (802-855), quarantine grant and expiry (860-911), waiver override/expiry/revoke (916-979), rollback catastrophic (1014-1026), JSON round trips (1031-1053), category regression blocks even without global regression (1079-1099), missing category fails closed (1102-1117), HWM monotone (1122-1136), floor not bypassable by waiver or quarantine (1185-1204), policy floor cannot be configured below canonical (1207-1219), NaN/∞ fail closed (1246-1257). A broken ratchet would be caught.

**Status.** Partial (complete and well tested; not wired).

**Cairn.** Home: CALIBRATION LAYER (with a SELECTOR AUDIT use). The ratchet is the right mechanism for the calibration tag itself: a claim's tag (SPECULATION → CONJECTURE → STRONG-EMPIRICAL → PROVEN) may move up only via Allow; a move down is a Block unless an attributed, reason-bearing, expiring waiver or quarantine exists; and some floor (e.g. "PROVEN requires a checked proof artifact") is non-waivable. The same shape fits the small-scale ladder ("measured scaling fit quality may not regress across runs") and the selector audit ("greenlight precision HWM"). Cost: ~250 lines plus a JSON state file. Tag STRONG-EMPIRICAL. Epistemics risk: the ratcheted quantity here is a statistical lower bound; for Cairn it must be a discrete tag or a deterministic measurement, otherwise the ratchet launders a posterior into a guarantee.

---

## 10. `crates/fsqlite-harness/src/drift_monitor.rs` (1190 lines)

**Mechanism.** Per category a `CategoryEProcess` (177-262): factor `1 + λ(x − p0)` with `max(0, ·)`, capped, sticky reject (219-236); defaults p0 = 0.05, λ = 0.8, α = 0.01, cap 1e12 (88-104); no λ validation (203-216). Plus a "BOCPD" `DriftDetector` from `replay_harness.rs` that is an EMA baseline comparator: after warmup, regime = Stable if `|rate − EMA| < sensitivity`, else Improving/Regressing by sign, and `ShiftDetected` on a regime transition (replay_harness.rs:767-779 struct, 796-841 `observe`); windows of 5 observations (95, 311-327). Alarms (459-529): level = max of e-value thresholds (Warning ≥ 10, Critical ≥ 100 = 1/α), raw-rate thresholds (0.3/0.5), and regime (ShiftDetected → Warning, Regressing → Info); runbook text per level (670-713); snapshot JSON (420-455, 590-650). Feeds: `observe_category` (370-375), `observe_batch(cat, mismatches, total)` feeds `i < mismatches` — all mismatches first (378-385), `observe_from_gate_report` feeds passing as matches then failing as mismatches from a static report (392-409).

**Math.** The update rule is fine for the defaults (factors 0.96 and 1.76); an out-of-range λ clamps to 0 (kills the process — safe direction). The problem is the data, not the rule: a static inventory fed in a fixed order is not a sequence of observations. With sticky rejection, order matters (mismatches first can cross the threshold mid-batch); re-feeding the same snapshot double-counts; and Ville's inequality says nothing about a quantity that is a deterministic function of one catalog state. In the one load-bearing feed, `release_certificate.rs:1556-1563`, `mismatches = cat_count − min(stat.verified_invariants, cat_count)` uses the **global** verified count (`CatalogStats` has only `verified_invariants` and per-category *totals*, parity_invariant_catalog.rs:294-313), so whenever the global verified count is ≥ every category's size the monitor sees zero mismatches and `drift.any_rejected` (1494, which rejects the certificate) cannot fire; when it does fire it is a threshold on a meaningless difference. The "BOCPD" and "statistically significant change point" labels (10-12; replay_harness.rs:642-651) describe an EMA comparator with a fixed sensitivity.

**Decision.** Wired: release certificate rejection on `any_rejected` (release_certificate.rs:1494, fed at 1556-1563); `adversarial_search.rs:512-560` uses it as a detection-power probe on a genuine random stream (100 baseline at 2%, then 200 at 10-60%) — that usage is legitimate.

**Tests.** 719-1190: factor pinned (794-805), power (779-791, 1126-1143), zero-violation "null" (759-776, 1103-1121 — not the null), batch counts (862-869), gate-report feed only checks observation counts (874-894), alarm ordering/runbooks (1001-1045). Nothing tests the release-certificate feed (different file), so the vacuous feed is invisible to the suite.

**Status.** Real (wired) but the wired feed is broken/vacuous; the monitor is fine for real streams.

**Cairn.** Home NONE as wired. For the SELECTOR AUDIT, "greenlit problem panned out: yes/no" **is** a genuine Bernoulli stream, and a fixed-λ e-process with tiered alarms and a runbook entry per level (459-529, 670-713) is a reasonable shape for "our selector's miss rate has drifted above baseline." Tag CONJECTURE. Epistemics risk HIGH as a cautionary example: feeding a static inventory into an anytime-valid monitor and labeling the output "drift."

---

## SYNTHESIS

Three mechanisms are worth re-implementing for Cairn; none are the headline e-process machinery.

1. **The ratchet (ratchet_policy.rs) → CALIBRATION LAYER.** Cairn's tag ladder has no no-regress rule. The ratchet supplies one: a tag moves up only through Allow; a down-move is Block unless an attributed, reason-bearing, expiring waiver or quarantine is on file; a non-waivable floor (PROVEN requires a checked proof artifact) sits under everything; history is persisted. Complete and well tested (761-1257). Ratchet a discrete tag or a deterministic measurement, never a posterior.

2. **Mechanical gate runner (verification_gates.rs) + fail-closed policy skeleton (confidence_gates.rs) → GATE LAYER.** Declarative plan, expected exit codes including expected-failure greps, ordered scopes where an earlier failure blocks and records why, raw output retained, invalid config → Fail, waiver flag mandatory in serialized config, external enforcement can only downgrade. This is the "mechanical, immutable checks" layer with working code to crib.

3. **Split-conformal threshold (sheaf_conformal.rs:360-384) → SMALL-SCALE LADDER / SKILL SELF-TESTS.** Forty lines, correct quantile, marginal coverage under exchangeability. Flags a 60-bit residual or a known-answer-test cost as anomalous at level α against the calibration pool; it says nothing about the asymptotic.

Secondary, only where a genuine sequential stream exists: the SSI gate's state machine with deterministic audit sampling (ssi_eprocess_gate.rs:312-347), and the evidence ledger plus arithmetic-mean aggregation in harness/eprocess.rs. For the primitive itself, the fsqlite-types version is enough; the rest is domain plumbing around that one line.

Homeless cleverness: conformal_martingale.rs and regime_monitor.rs (no callers; window dependence undercuts the Ville claim); evalue_eviction.rs (an aged access counter in e-process costume, never consulted for eviction); OpportunityScore (a typed-in "confidence" multiplied into a pass/fail gate); drift_monitor.rs as wired (a static catalog fed to an anytime monitor through a global-vs-per-category count bug that makes the release-rejection path vacuous, release_certificate.rs:1556-1563, 1494).

Biggest misuse risk: letting non-rejection by a sequential test act as positive evidence. The SSI gate docstring claims α bounds the missed-pivot rate (59-64) when Ville only bounds false alarms; evalue_eviction reads 1/e as "probability the page is hot" (24-29, 319-325); confidence_gates calls a shrunk completion fraction a "mismatch probability" (701-728). The repo's own best practice is the counter-rule: harness/eprocess.rs asserts hard invariants deterministically and gives the e-process only to a stochastic rate (338, 1971-1984). Cairn should state it as a gate-layer invariant: a statistical monitor may block a promotion or raise an alarm; it may never promote a tag.
