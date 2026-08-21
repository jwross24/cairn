# Focus brief — the calibrate / evidence / certificate family (frankengraphdb, frankensearch, frankenfs)

Scope: code-level read of one mechanism family across three cloned repos, for the Cairn design review. Code over docs; every `file:line` below was printed during the read. Repos (read-only): `frankengraphdb` @ cfac16678c6a (default branch), `frankensearch` v1.6.0 @ 4302c377, `frankenfs` v0.2.0 @ 77b0a032; the statistical cores fgdb wraps live in `asupersync` (cloned, pinned rev in `fgdb-calibrate/Cargo.toml`).

Questions answered: (1) fgdb-calibrate eprocess/conformal/exploration + wrapper identity laws + "sextant"; (2) fgdb-evidence; (3) frankensearch recall certificate; (4) frankensearch fusion conformal + decision plane; (5) frankensearch canonicalize/generation/generation_root; (6) frankenfs e-process. Part A is the parent's read; Parts B and C were read by forks and their headline claims were spot-checked by the parent (recall-certificate rank rule and struct contents, adaptive-α direction, phase-gate e-factor, frankenfs e-process absence).

Evidence-tag legend: PROVEN-in-source = math verified by reading AND tests read; STRONG-EMPIRICAL = behavior verified, tests seen, no theorem claimed or claimed theorem approximate; CONJECTURE = the stated guarantee is not established by the code as written.

## Part A — frankengraphdb (Q1, Q2)

Repo root: `scratchpad/repos/frankengraphdb` @ cfac16678c6a. Paths below are relative to `crates/`. The statistical cores live in `asupersync` (cloned at `scratchpad/repos/asupersync`, rev pinned in `fgdb-calibrate/Cargo.toml`); fgdb-calibrate is by its own charter a *wrapper* (`fgdb-calibrate/src/lib.rs:3-7`: "binds statistical cores supplied by asupersync to complete, immutable FrankenGraphDB trial identities").

**Who consumes fgdb-calibrate (load-bearing vs vestigial).** `rg fgdb_calibrate` outside the crate hits only `fgdb-sim/src/campaign.rs:42` and `fgdb-sim/tests/sim_campaign.rs:11` (both `exploration::*`), plus the crate's own tests. `EProcessTrial` and `GraphMetricConformal` have no constructor outside `fgdb-calibrate/{src,tests}`. The repo's own reality check agrees: `docs/REALITY_CHECK_AND_BRIDGE_PLAN.md:47` — "`fgdb-calibrate` as a real Sextant library with no product controller consuming it." So: exploration.rs is load-bearing (for the sim harness only); eprocess.rs and conformal.rs are real, tested, and product-vestigial.

**What "Sextant" is.** The plan's name for the calibration plane within bet B5 (`COMPREHENSIVE_PLAN_FOR_THE_DESIGN_OF_FRANKENGRAPHDB.md:1110-1112`): "Sextant supplies e-processes, conformal predictors, sequential tests, robust estimators, regime/change detectors, and propensity/OPE tooling as deterministic transformations of logged inputs. It governs performance and operational choices; it never upgrades assumption-bearing evidence into exact correctness." The plan's stated failure mode is instructive (`:1377`): "The calibration plane becomes ornamental math (monitors nobody gates on) … Every Sextant artifact binds to a named decision card, `evidence.toml` row, or `slo.toml` row — or is removed as dead instrumentation." `tests/sextant_e2e.rs` is the crate-level end-to-end: runs every monitor under the lab runtime, builds the statistical log + envelopes + a policy-epoch promotion, then asserts sticky revert on regime shift (`sextant_e2e.rs:2507` `sextant_evidence_promotes_then_stickily_reverts_on_regime_shift`).

**What "wrapper identity laws" are.** `tests/wrapper_identity_laws.rs:1-30`: the crate "does not implement a second statistical engine", so the central law is *differential*: wrapper and bare asupersync core fed the identical sequence must agree on the statistic bit-for-bit (compared on canonical float bits, `-0.0` collapsed, `:64-71`). Four families: (1) identity preservation — `EProcessTrial` vs `EProcess` (`:96`), sensitivity to one perturbed outcome (`:166`), `DrainProgressMonitor` vs `ProgressCertificate` (`:231`); (2) decision log append-only & totally ordered (`:536,:579,:607`); (3) adaptive-decision contract — every decision names its pinned fallback and selects one of exactly two declared identities (`:382,:423,:440`); (4) policy-epoch monotonicity (`:645,:665`). Test inputs are fixed literals at domain boundaries; no clock, no entropy.

---

### A1. `fgdb-calibrate/src/eprocess.rs` (1215 lines) + core `asupersync/src/lab/oracle/eprocess.rs`

**Mechanism (precise).** Core (asupersync): binary betting martingale. `E_0 = 1`; per observation `X_t ∈ {0,1}`: `factor = 1 + λ(X_t − p0)` (`asupersync eprocess.rs:224-228`, via `mul_add`), `E_t = min(E_{t-1}·factor, max_evalue)` (`:234-239`), sticky rejection when `E_t ≥ 1/α` (`:250-253`), `rejection_time` recorded once. Config validation (`:112-157`): `p0 ∈ (0,1)`, `λ ∈ (−1/(1−p0), 1/p0)` (exactly the range keeping both binary factors > 0), `α ∈ (0,1]`, `max_evalue ≥ 1/α` (else rejection impossible). Null: `P(X_t=1 | F_{t-1}) = p0` (or one-sided `≤ p0` for λ>0 / `≥ p0` for λ<0 — both give a supermartingale). No mixture over λ, no adaptive λ (fixed bet); no resets exposed by the wrapper.

Wrapper (fgdb): `TrialIdentity` = {monitor_oid, filtration_oid, SequenceWindow[first..=last], regime_epoch, candidate_decision_oid, pinned_fallback_oid}, candidate ≠ fallback enforced (`eprocess.rs:140-152`). `EProcessProfile` stores p0/λ/α/max_evalue as canonical IEEE-754 bits (`:203-225`, `-0.0→0.0` at `:757-764`). `observe()` (`:656-733`) rejects identity/profile mismatch, non-next sequence, window-complete, counter overflow *before* mutating the core; then `core.observe(value==One)`; records `first_rejection_sequence` once. `EvidenceRecord` (`:404-415`) = identity, profile, through_sequence, observations, one_observations, e_value_bits, rejection_threshold_bits, first_rejection_sequence, `PolicyOutcome`. Outcome (`:716-721`): `core.rejected ? PromoteCandidateAgainstPinnedFallback : RetainPinnedFallback`; outcome fields are private so it cannot be re-attached to other policy OIDs (`:342-347`). Direction is profile-defined: negative λ makes `Zero` the growing outcome (`:263-268`, test `:891`).

**Correctness verdict.** Nonnegativity: guaranteed by the validated λ range; the `factor.max(1e-15)` clamp (`asupersync:231`) is dead under validation. `E[factor | F_{t-1}] = 1 + λ(p − p0) ≤ 1` under the (one-sided) null → supermartingale → Ville. Capping at `max_evalue ≥ 1/α` keeps `E' ≤ E` pointwise by induction, so `P(sup E' ≥ 1/α) ≤ α` still holds. Sticky rejection is exactly the Ville event. No averaging, no resets in the wrapper (fixed window, `next_sequence` goes to `None` at window end, `:693-699`). Two nits: (i) the module doc states the λ interval backwards, `(-1/p₀, 1/(1−p₀))` (`asupersync:36-37`), while `validate()` has it right (`:127-131`); (ii) the NaN guard sets `current = max_evalue` (`:237-239`), which *rejects* — for asupersync "reject" = alarm (conservative), but for fgdb reject = *promote candidate* (anti-conservative); unreachable with validated finite config and binary input, but the wrapper inherits the asymmetry. Power: fixed λ is not growth-optimal; for small effects this is slow (not a validity defect).

**Decision it drives.** Two-outcome policy gate: keep the pinned deterministic fallback vs. promote a candidate decision policy, bound to the trial's OIDs. In the graph DB: nothing yet (no product caller). In `sextant_e2e.rs:2545-2549` the e-process outcome is one of four evidence inputs to a `DecisionPolicyEpoch` promotion.

**Tests.** Unit: `eprocess.rs:784-1215` (construction validation `:822`, canonical float bits `:861`, negative-λ bounds `:873`, negative bet promotes on zeros `:891`, identity/profile retained `:939`, sequencing failures do not advance state `:974`, bit-identical replay `:1007`, retain-until-reject-then-promote `:1038`, mismatches non-mutating `:1093`, window end `:1149`, u64::MAX window `:1168`). Differential: `wrapper_identity_laws.rs:96,:166`. Statistical: `sextant_e2e.rs:1095` — 8192 null trials, horizon 128, α=0.05, p0=0.25, λ=1, peek after every prefix, stop at first rejection; asserts empirical type-I ≤ α + one-sided Hoeffding margin at confidence 1e-6 (`:1142-1151`), plus a planted alternative (p=0.75) must reject ≥ 95% (`:1182-1188`). asupersync core unit tests `asupersync eprocess.rs:597-830`.

**Status.** Real, well-tested library; product-vestigial (no graph-DB controller calls it).
**Cairn home.** SELECTOR AUDIT (binary "greenlit problem panned out?" stream against a declared base rate p0; anytime-valid; decision = keep current selector vs revert to fallback heuristic). The same primitive gives the CALIBRATION LAYER its missing quantitative small-numbers threshold (`E_t ≥ 1/α` is the number).
**Cost.** Core ≈ 30 lines; identity-binding wrapper ≈ 150 lines if you want bit-exact replay evidence. O(1) per observation.
**Evidence tag.** PROVEN-in-source (math verified; unit + differential + simulated type-I tests read).
**Epistemics risk.** The null is a *declared constant* p0; if the selector's base rate is unknown, p0 is an assumption, not a fact. Fixed λ has weak power at small effects. Multiplicity across *trials* is not controlled (each `TrialIdentity` is its own Ville bound); an operator who opens a fresh trial after each non-rejection re-inflates error. The wrapper prevents resets *within* a trial, not across trials.

---

### A2. `fgdb-calibrate/src/conformal.rs` (1708 lines) + core `asupersync/src/lab/conformal.rs`

**Mechanism (precise).** Split conformal with a hard calibration/assessment phase boundary. Core (`HealthThresholdCalibrator`): `calibrate(metric, v)` appends finite values (`asupersync conformal.rs:746-757`); `check(metric, v)` (`:764-813`) computes, for `ThresholdMode::Upper`, score = v, threshold = `conformal_quantile(cal_values, α)`; for `TwoSided`, median m of the calibration set, scores `|cal_i − m|`, test score `|v − m|`, same quantile. `conformal_quantile` (`:542-565`) = the `ceil((1−α)(n+1))`-th smallest calibration score (1-indexed); returns `+∞` when that rank exceeds n (α < 1/(n+1)) — the comment cites the bug they fixed (`br-asupersync-mdym3s`: clamping to the max score only gives n/(n+1) coverage). Conforming iff `score ≤ threshold`; `coverage_target = 1 − α`.

Wrapper (`GraphMetricConformal`, `conformal.rs:766-1090`): identity = {graph population, selection policy, window, regime, candidate, fallback} (`GraphMetricIdentity`, `:204`); profile = {α bits, mode, min/max calibration samples} (`:313-389`), hard caps `MAX_CALIBRATION_SAMPLES = 2^20` (`:17`) and `MAX_CONFORMAL_TRIAL_OBSERVATIONS = 2^21` (`:23`); construction requires max_cal < window length so there is assessment capacity (`:801-813`). `calibrate()` (`:883-928`) rejects after phase closes or at the cap; `assess()` (`:930-1068`) permanently closes calibration on first call (`:1043`), then selects `CandidateDecision` only when *all* hold: foundation ready, value finite, foundation statistics finite, foundation calibration count == wrapper count, `conforming`, **and realized running coverage ≥ coverage_target** (`:963-1000`). Every other path → `PinnedFallback` with a named `AssessmentDisposition` (`:483-502`). Evidence carries value/threshold/score/coverage bits and exact counters (`:553-571`).

**Correctness verdict.** Upper mode: exact finite-sample marginal coverage `P(score_{n+1} ≤ q̂) ≥ 1−α` under exchangeability of the n+1 values; the `+∞` convention is right. TwoSided: the median is fit on the calibration set itself, so calibration scores and the test score are not strictly exchangeable (each cal point's score uses a median that includes it; the test score uses one that excludes it). The comment "preserving exchangeability" (`asupersync:790-793`) overstates; the leak is O(1/n) and harmless at n=64, but it is an approximation, not the theorem. The wrapper's **realized-coverage gate** is a heuristic, not a guarantee: it compares the running empirical coverage (including the current point) against 1−α with no confidence band, so a single non-conforming assessment early on pins the fallback for the next several assessments even though the calibration is valid — unit test `conformal.rs:1549-1574` shows exactly this: after one outlier, a conforming 5.0 is pinned with coverage 2/3. Conservative (fail-closed), so it cannot break validity; it does make "candidate selected" mean "conformal ∧ running coverage ≥ target", which is stricter than the conformal set and has no stated error rate of its own. Frozen calibration set after first assessment means no adaptation under drift (by design; see the drift test).

**Decision it drives.** Per-assessment: candidate policy vs pinned fallback, i.e. "this metric value is inside the calibrated prediction set → allow the adaptive policy". Product caller: none.

**Tests.** Unit `conformal.rs:1186-1708` (construction bounds `:1187`, non-finite and sequencing rejections non-mutating `:1310`, readiness `:1348`, early assessment pins fallback & closes calibration `:1363`, outlier → fallback `:1402`, vacuous `+∞` threshold cannot select candidate `:1436`, count mismatch → fallback `:1470`, bit-exact replay `:1494`, realized-coverage gate `:1549`, regime change → fallback `:1607`). Statistical: `sextant_e2e.rs:1197-1296` — 8192 trials, 64 calibration draws, α=0.1, one held-out draw: asserts empirical coverage + Hoeffding margin(1e-6) ≥ 0.9, and a planted shift of +1e6 drives coverage ≤ 0.05 (`:1272-1295`). Core: `asupersync conformal.rs:949-1161` incl. `conformal_quantile_infinite_when_rank_exceeds_n` (`:980`).

**Status.** Real, tested; product-vestigial.
**Cairn home.** PROPORTIONAL-SCRUTINY ROUTER — a distribution-free, calibrated anomaly threshold ("send to heavier review iff nonconformity > q̂_{1−α}") with a stated false-alarm rate under exchangeability. Reimplement Upper mode only.
**Cost.** ≈ 40 lines (sort + rank). O(n log n) per check as written (they re-sort every call); O(log n) with a sorted multiset.
**Evidence tag.** PROVEN-in-source for Upper mode (math + tests incl. coverage simulation). TwoSided: STRONG-EMPIRICAL. Realized-coverage gate: heuristic (no theorem).
**Epistemics risk.** Exchangeability is the whole guarantee; agent-generated claims across a research session are ordered, correlated, and subject to selection — coverage is *marginal* and can fail badly per-stratum. Their frozen calibration set is a deliberate stance; Cairn would need explicit recalibration epochs.

---

### A3. `fgdb-calibrate/src/exploration.rs` (1476 lines) + core `asupersync/src/lab/exploration_budget.rs`

**Mechanism (precise).** Not a bandit. An *exploration-budget stopping rule* over a binary novelty series ("did run t discover a new equivalence class?"). Core (`asupersync exploration_budget.rs:166-202,227-261`): `p̂ = discoveries/n` (1.0 before any sample), upper bound `U = min(1, p̂ + sqrt(ln(1/α) / (2n)))` (Hoeffding one-sided; `U = 1` while `n < min_samples`), `target_met ⇔ U ≤ 1 − target_coverage`, `recommended_additional_runs` = smallest k ≤ `max_additional_runs` such that appending k zeros makes the bound meet the target (projected, not observed), `exhausted_recommendation` when k hits the cap without meeting. The estimator's own assumption record (`:67-85`): exchangeable runs, binary novelty, "additional runs hit existing classes". Wrapper (`ExplorationBudgetMonitor`, `exploration.rs:739-923`): identity {budget, window, regime oids, regime_epoch, [first..=last], candidate, fallback}; profile {α, target_coverage, min_samples, max_additional_runs, max_observations, estimation-work ceiling `:18-21,:957-969`}; caller-supplied `ExplorationAssumptionAttestation` (`:141-193`) must dominate the estimator's required assumptions or the disposition is `AssumptionsUnsupported` → fallback (`:925-943`). `observe()` is preflighted & atomic (`:821-875`). Disposition order: unsupported → insufficient samples → exhausted → target not met → `CandidateSupported` (`:925-943`).

**Correctness verdict.** (a) It is labeled "conformal" (`conformal_upper_bound`, `asupersync:1-7,:104`) but the bound is Hoeffding for a Bernoulli mean — a fixed-n CI, not a conformal set. (b) Hoeffding assumes independent bounded summands; the discovery indicator is a species-accumulation process whose success probability *decreases* as classes are found, so the draws are neither iid nor exchangeable; the estimate of "next run is novel" via discoveries/n is crude (the first run is always a discovery → conservative early; the principled estimator is Good–Turing missing mass). (c) The monitor re-evaluates after every observation, and the only consumer stops at the *first* `CandidateSupported` (`fgdb-sim/src/campaign.rs:785-792`), i.e. optional stopping with a fixed-n bound and no time-uniform correction — the nominal α is not honored under that stopping rule. Nonnegativity/monotonic bookkeeping is fine; the *guarantee* is heuristic. To their credit, the log line literally says `unexplored-space=uncharacterised` (`campaign.rs:801`) and the outcome is `NotFalsified` under a named sampling model, never "exhausted" (`campaign.rs:18-39,:138-142`).

**Decision it drives.** In `fgdb-sim` (the one product consumer): `run_model_qualified_campaign` (`campaign.rs:741`) stops a lab fuzz/DPOR campaign and reports `CampaignOutcome::NotFalsified { sampling_model, explored }` with `ClaimClass::Statistical` (`:128-142`); a falsification always wins (`:767-777`); an inconclusive sample is a hard error, never a data point (`:778-780`).

**Tests.** Unit `exploration.rs:1033-1476` (invalid inputs `:1034`, work/window limits `:1131`, atomic rejections `:1161`, candidate after min samples `:1212-1245`, each unsupported assumption pins fallback `:1247`, exhausted/unmet → fallback `:1275`, bit-exact projection `:1417`, replay identical `:1461`). Product: `fgdb-sim/tests/sim_campaign.rs:276` (`model_qualified_stopping_uses_the_foundation_bound_and_names_its_assumptions`), `:464` (unsupported assumptions → fallback), `:405` (known counterexample can never be `NotFalsified`). Core: `asupersync exploration_budget.rs:267-375`.

**Status.** Real and load-bearing for `fgdb-sim`; the only fgdb-calibrate module with a non-test consumer.
**Cairn home.** ORCHESTRATOR — only as the *shape* of a "diminishing-novelty stop" signal for a research branch (rate of genuinely new lemmas/ideas per unit compute) with explicit attested assumptions; not as the bound itself. NOT a bandit; does not address "expected information per compute-dollar".
**Cost.** 20 lines. Trivial.
**Evidence tag.** STRONG-EMPIRICAL for the engineering (tests, atomicity, attestation → fallback); CONJECTURE for the stated 1−α (mislabeled conformal; non-iid; optional stopping).
**Epistemics risk.** The name "conformal" will be read as a guarantee it does not carry; a Cairn operator could cite `target_met` as "95% of the idea-space is covered". Borrow the attestation-or-fallback discipline, not the number.

---

### A4. `fgdb-calibrate/src/log.rs` (7899 lines; read: header, digest/identity traits, log struct, append, order) — the "statistical decision log"

**Mechanism.** `StatisticalLogRecord` binds a closed monitor-kind vocabulary and statistic to evidence/stream/regime/candidate/fallback/terminal-action identities; there is *no* claim-class field to set — `claim_class()` is derived and a `compile_fail` doctest pair proves the absence (`log.rs:1-58`). `StatisticalDecisionLog` (`:2522-2625`): bounded vector; `append()` rejects duplicates, per-monitor batches that are not strictly later, and any record not strictly greater under `canonical_record_order` (`:3934-3952`: batch → monitor kind → monitor oid → evidence oid → window → epoch → candidate → fallback → selected → statistic); all checks precede the push (atomic). Evidence OIDs are issued/verified by a namespace-aware authority trait (`StatisticalEvidenceIdentityIssuer/Verifier`, `:206-235`); an unkeyed `StatisticalEvidenceDigest` (`:162-179`) exists only to detect transcript drift and is explicitly *not* an ObjectId. **Not hash-chained** — no previous-record pointer; ordering, not linkage, is the integrity property.
**Tests.** `wrapper_identity_laws.rs:536,:579,:607`; in-file tests around `:7421,:7676`.
**Status.** Real, product-vestigial. **Home.** CLAIMS DB (append-only, totally ordered decision records with no mutable claim class). **Tag.** STRONG-EMPIRICAL (structure read, tests named, math N/A). **Risk.** 7.9k lines for a log is over-engineering at Cairn's scale; take the three rules (append-only, total order, class is derived not stored), not the codec.

---

### A5. `fgdb-evidence/src/lib.rs` (1982 lines) + `fgdb-claim/src/lib.rs` (758 lines, read for the lattice)

**What an "evidence" record is.** An `EvidenceEnvelope` (`lib.rs:1099-1108`) = `{claim: EvidenceClaim, evidence_oid, selection_policy_oid, strata_identity, propensity_support_identity, calibration_window: Option<[start,end)>, regime_epoch, fallback}`. Private fields; construction only via `new` (`:1159-1179`); supersession = a new envelope (doc `:1040-1066`, compile_fail doctests show field construction and mutation do not compile). `FallbackBehavior` (`:842-849`) = `DeterministicPolicy{policy_oid} | FailClosed` — the fallback is *part of the evidence identity* ("no adaptive controller ships without its conservative deterministic fallback"). `StrataIdentity`/`PropensitySupportIdentity` (`:789-838`) are `NotApplicable | Bound(oid)` — explicit N/A, not a sentinel.

**Claim kinds and the lattice** (`fgdb-claim/src/lib.rs:484-521,:535-549`): `SafetyInvariant{invariant_id}` → Invariant; `FormalModelClaim{model, boundary, checked_bounds, refinement_status}` → Proof if `RefinedToImplementation`, else BoundedModel; `StatisticalClaim{population, sampling_rule, error_control(α or N/A), power_or_ESS, assumptions[]}` → Statistical; `ConfigurationModelClaim` → Statistical; `EmpiricalGate{fixture, machine_profile, sample_count, variance_budget, comparison_rule}` → Benchmark. Strength ranks Invariant 5 > Proof 4 > BoundedModel 3 > Statistical 2 > Slo 1 > Benchmark 0 (`:60-65`); `try_justify(target)` succeeds iff `strength(self) ≥ strength(target)` and returns a typed `Justification` or `LatticeViolation` carrying both classes — never a bool (`:70-85`). `EvidenceEnvelope::justify` applies it at the envelope boundary (`lib.rs:1299-1301`). Routing law (`fgdb-claim:88-98`): Invariant → invariants.toml; Slo → slo.toml; everything else → evidence.toml; the registry file header restates the doctrine (`registries/evidence.toml:8-16`: "A monitor that drives no named decision is dead code, but binding it to a decision does not make it an invariant").

**Hashing / content addressing.** `to_canonical_binding_bytes` (`lib.rs:1212-1241`): domain string `fgdb:evidence-envelope-binding:v2` length-prefixed, version u16 LE, field count 8, then 8 tagged length-delimited fields; the claim itself is encoded with a (variant, field-count) header and tagged fields (`:904-986`), floats as IEEE bits (α at `:944`). `binding_address_with(hash)` (`:1244-1246`) injects the project hash kernel — the crate carries no crypto dependency (`Cargo.toml`: only fgdb-claim, fgdb-types). The `evidence_oid` is the content address of the evidence *body*, issued elsewhere.

**Chaining / linking decisions to observations.** No hash chain and no prev pointer. Linkage is by reference: a `DecisionPolicyEpoch` promotion carries `evidence_refs` equal to the sorted evidence OIDs of the statistical-log records that justified it (`sextant_e2e.rs:2562-2588`), and each record's envelope binds `selection_policy_oid`, `strata`, `propensity_support` (OPE rows bind the support evidence OID, `:2576-2584`). So the pattern is an *evidence-reference DAG keyed by content address* with an *ordered append-only decision log*, not a ledger in the blockchain sense.

**ReplayCompleteness** (`lib.rs:459-464,:597-645,:647-676`): four grades `Replayable | StructuralReplay{reproduced, omitted} | VerifiableIfArtifactsSupplied{missing} | AuditOnly{missing_or_redacted}` over a closed, versioned 36-class `ReplayClass` vocabulary (`:28,:40-77`); `meet` is commutative/associative/idempotent and conservative (structural ⊓ supplyable → AuditOnly, `:626-640`); `weaken_for_redaction` drops to AuditOnly on any actual redaction. This is exactly a "how replayable is this evidence" lattice.

**Tests.** Unit `lib.rs:1327-1982`: four validated arms `:1327`, vocabulary versioned/complete/ordered `:1377`, weaker grades cannot alias stronger with empty sets `:1461`, meet laws `:1685`, mixed meet conservative `:1740`, windows reject empty/inverted `:1855`, envelope binds immutable context `:1912`, justification exhausts every claim kind × target `:1947`. Integration `tests/evidence_relations.rs`: address changes for every bound component `:463`, identical content → one address independent of allocation `:541`, seeded boundary corpus stable `:613`, mandatory fallback for every claim kind `:697`.

**Status.** Real, tested; consumed by fgdb-calibrate log/policy_epoch and a delta-types example; no product writer.
**Cairn home.** CLAIMS DB — (i) claim-kind ⇒ maximum justifiable class with a typed `justify` gate is a direct template for PROVEN / STRONG-EMPIRICAL / CONJECTURE / SPECULATION with "a weaker tag may inform but never justify a stronger one"; (ii) mandatory declared context per kind (population, sampling rule, α, assumptions) and mandatory fallback; (iii) `ReplayCompleteness` for the SUBSTRATE's "replayable vs certificate-only vs audit-only" grades.
**Cost.** Lattice + envelope ≈ 200 lines; completeness lattice ≈ 150 lines.
**Evidence tag.** PROVEN-in-source (structural properties verified; exhaustive lattice tests read).
**Epistemics risk.** The machine enforces the *lattice*, not the *truth* of declared context — `population`, `sampling_rule`, `assumptions` are free strings. A STATISTICAL envelope with a false `assumptions` list is still well-typed. Cairn must pair this with the calibration layer's checks, not treat the envelope as evidence of validity.

## Part B — frankensearch (Q3, Q4, Q5)

Repo: `frankensearch` @ 4302c377169c97d52296efa77fc37e66429aad44 (v1.6.0). All paths below are relative to the repo root. Every `file:line` cited was printed during this read. Call-site censuses were done with `rg` across the whole repo (`-g '*.rs'`), excluding the file under review.

---

### B.1 `crates/frankensearch-index/src/recall_certificate.rs` (612 lines) — Q3

**Mechanism (precise).** Three pure-std functions over a *calibration sample* of measured per-query recall@k values in [0,1], plus two drivers:

- `conformal_recall_lower_bound(recalls, alpha)` (`recall_certificate.rs:50-73`): split-conformal one-sided lower tolerance bound. Filters non-finite, sorts ascending, `rank = floor(alpha*(n+1))`; if `rank == 0` returns the trivial bound `0.0` (`:65-68`); else returns the `rank`-th smallest (1-indexed) clamped to [0,1] (`:71-72`). Guarantee: for an exchangeable fresh query, `P(recall_new >= L) >= 1-alpha`. This is the standard rank-uniformity argument: the fresh value's rank among n+1 exchangeable values is uniform, so `P(fresh < r-th smallest) <= (r-1)/(n+1)`... with r = floor(alpha(n+1)), `P(fresh < L) <= floor(alpha(n+1))/(n+1) <= alpha`. Correct (and conservative on ties).
- `mean_recall_lower_bound(recalls, delta)` (`:88-102`): Hoeffding LCB `mean - sqrt(ln(1/delta)/(2n))`, clamped. Correct for [0,1]-bounded iid.
- `mean_recall_lower_bound_bernstein(recalls, delta)` (`:122-138`): Maurer–Pontil empirical-Bernstein LCB `mean - sqrt(2 V_n ln(2/delta)/n) - 7 ln(2/delta)/(3(n-1))`, unbiased sample variance, `n<2 -> 0.0`. Matches the published bound.
- `certified_min_ef` / `certified_min_ef_mean` (`:165-191`, `:206-230`): ascending sweep over `(ef, recalls)` pairs, return first `ef` whose bound `>= target`, else the best-bound fallback with `meets_target=false`.
- `calibrate_certified_ef(candidate_efs, measure_recall, target, alpha)` (`:259-292`): lazy driver — dedups/sorts candidates, calls the expensive `measure_recall(ef)` closure ascending, short-circuits at the first certified `ef`, records the full `sweep` as an audit trail (`EfCalibration { chosen, sweep }`, `:234-242`).

**What the "certificate" actually is.** It is NOT a succinct proof object that a third party can verify without re-running anything. It is a *statistical* certificate: `CertifiedEf { ef_search, certified_recall, meets_target }` (`:144-152`) plus the `sweep`. The assertion is "a fresh exchangeable query will have recall@k ≥ L w.p. ≥ 1−α" (tail mode) or "E[recall] ≥ L w.p. ≥ 1−δ" (mean mode). What is stored is the chosen `ef`, the bound, the boolean, and the per-ef bounds measured. Verifying it means either trusting the calibration run or re-measuring: the calibration recalls themselves (`Vec<f64>` per ef) are consumed but not stored in `EfCalibration` — only the derived bounds are. So a verifier cannot recheck the order statistic from the struct alone. The *cost to produce* is `|candidates measured| × |calibration queries| × (one ANN search + one brute-force top-k)`; the live glue at `hnsw.rs:1350-1381` computes the exact top-k once per query (ef-independent) and re-runs only the ANN search per ef, short-circuiting at the first certified ef. A failed ANN search or exact-underfill fallback is scored as recall `0.0` for that (query, ef) (`hnsw.rs:2983-2991`), which is the conservative direction.

**Correctness verdict.** Sound as a statistical bound under exchangeability of calibration queries and the future query stream; finite-sample; trivial-bound fallback rather than an invented number when `floor(alpha(n+1))==0` (`:66-68`). Monotone in alpha. The soundness is relative to the *measured* calibration sample: if calibration queries are not exchangeable with production queries (distribution shift, adversarial queries), the guarantee is void — the code cannot detect this. The coverage tests are Monte-Carlo with a fixed LCG (`:353-383` conformal, `:397-419` Hoeffding, `:422-446` Bernstein), with tolerance `alpha+0.02` for the conformal one.

**Decision it drives.** `HnswIndex::certify_ef_search` (`hnsw.rs:1350-1381`) selects the cheapest `ef_search` meeting a recall target — the "automated recall-budget sign-off" for turning on aggressive ANN. The heuristic it replaces, `estimate_recall = clamp(0.9 + 0.1·log2(ef/k))` (`hnsw.rs:2960-2964`), remains as `AnnSearchStats.estimated_recall` with a doc pointer to the certified path (`hnsw.rs:279-286`).

**Tests.** Unit: `recall_certificate.rs:317-328` (trivial bound when n too small), `:331-337` (order statistic), `:340-347` (monotone in alpha), `:353-383` (coverage validity, 4000 trials), `:386-394`, `:397-419` (Hoeffding coverage), `:422-446` (Bernstein coverage), `:449-461` (Bernstein tighter than Hoeffding on low variance), `:464-496` (mean mode certifies cheaper ef), `:499-519` (min-ef selection and fallback), `:522-589` (lazy short-circuit and measure-all fallback), `:595-611` (catches heuristic overconfidence). End-to-end on a real HNSW + brute force: `hnsw.rs:3527-3578`.

**Status.** Real and tested, but **wired only into a bench and its own tests**: the only callers of `certify_ef_search` outside `hnsw.rs` are `crates/frankensearch-index/benches/real_embed_ann.rs:3,180`. No CLI/runtime path calls it (grep over `-g '*.rs'`). Library-complete, product-dormant.

**Candidate Cairn home.** SUBSTRATE — no, more precisely the pattern belongs to the **CALIBRATION LAYER** as the *shape* of a "quantitative gate": a declared target, a declared α, a measured calibration sample, a bound computed by a named finite-sample inequality, and the trivial bound returned when n is too small. It is NOT a substitute for Cairn's "succinct certificate for nondeterministic work" (see risk below).

**Cost.** Production: O(#calibration × (ANN + brute-force)). Verification of the arithmetic: O(n log n) once the sample is available. Re-implementation: ~150 lines.

**Evidence tag.** PROVEN-in-source (arithmetic verified against the standard rank argument, Hoeffding, and Maurer–Pontil; coverage tests present and read).

**Epistemics risk.** (1) Calling this a "certificate" invites confusing a *statistical guarantee under exchangeability* with a *verifiable proof object*. For Cairn's substrate (Pollard-rho run, ANN search), what is needed is a witness the verifier can check deterministically (e.g., the found factor, or for ANN the k returned ids + their distances + a brute-force spot-check seed). This module does not provide that; it provides a calibration bound. (2) The struct stores bounds, not the raw calibration sample; an auditor cannot recompute. (3) Exchangeability of calibration vs. production queries is assumed and unchecked. (4) Every number in the docs is on synthetic corpora (`docs/NEGATIVE_EVIDENCE.md:5414-5415`).

---

### B.2 `crates/frankensearch-fusion/src/conformal.rs` (905 lines) — Q4 (conformal half)

**Mechanism (precise).**
- `ConformalSearchCalibration` (`conformal.rs:23-26`): stores sorted 1-indexed *ranks of the relevant document* as nonconformity scores (higher rank = worse). `calibrate` rejects empty and rank 0, sorts (`:82-105`). Custom `Deserialize` rejects empty / zero / unsorted / `n_calibration != len` (`:34-72`).
- `required_k(alpha)` (`:129-156`): `quantile_index(n, 1-alpha)` = `ceil((n+1)(1-alpha))` clamped to [1, n] then 0-indexed (`:467-481`), returns that order statistic. This is the split-conformal quantile `q̂ = ⌈(n+1)(1−α)⌉`-th smallest score; the prediction set "top-k with k = q̂" covers the relevant doc w.p. ≥ 1−α under exchangeability.
- `p_value(observed_rank)` (`:214-232`): `(#{score >= observed} + 1)/(n + 1)` — the standard conformal p-value, super-uniform under exchangeability. Correct.
- `rank_prediction_interval(alpha)` (`:178-195`): two-sided, `quantile_index(n, alpha/2)` and `quantile_index(n, 1-alpha/2)`. Approximately valid (lower side uses ceil where floor would be the conservative choice; minor).
- `MondrianConformalCalibration` (`:240-351`): per-`QueryClass` calibration when a class has ≥ `min_examples_per_class` examples, else global fallback. Class-conditional (Mondrian) conformal — valid per class given exchangeability within class.
- `AdaptiveConformalState` (`:358-442`): `alpha_t = clamp(alpha_{t-1} + gamma*(err_t - alpha_{t-1}), 1e-6, 1-1e-6)` (`:356`, `:425-431`).

**Correctness verdict.**
- Split conformal quantile and p-value: **correct**, with one soundness gap: when `ceil((n+1)(1-alpha)) > n` (i.e. `n < (1-alpha)/alpha`, e.g. n < 9 at α=0.1, or any n at α=0), the valid prediction set is "all ranks" (infinite); the code clamps to the max observed rank (`:479`) and the test `required_k_with_alpha_zero_returns_max` (`:809-814`) enshrines that. So for small n the returned k is *not* guaranteed to cover at 1−α. Contrast `recall_certificate.rs:66-68`, which returns the trivial bound in the analogous case. The doc comment calls the fallback "most conservative" (`:127`) — it is the most conservative *finite* k, not a valid one.
- Adaptive alpha: **not ACI**. Gibbs–Candès adaptive conformal inference updates `alpha_{t+1} = alpha_t + gamma*(alpha_target - err_t)` — miscoverage above target *lowers* alpha (bigger sets). Here alpha moves *toward* the observed error (`:425-431`; test `:534-540` asserts `alpha_after > alpha_before` when err 0.3 > alpha 0.1). With `required_k` decreasing in alpha, higher observed error → higher alpha → smaller k → less coverage: positive feedback, no long-run coverage guarantee. And in the only production wiring, "observed_error_rate" is not miscoverage at all but `1 - (kendall_tau+1)/2` between fast and refined rankings (`searcher.rs:2932-2935`) — a rank-disagreement proxy. The guarantee chain is broken at both links.

**Decision it drives.** In `TwoTierSearcher`, `conformal_candidate_target(k) = max(k, required_k(alpha))` inflates the Phase-1 candidate pool (`searcher.rs:2878-2895`, used at `:1563-1565`); `maybe_update_adaptive_conformal(tau)` runs after Phase-2 blend (`:2365`, `:2924-2947`). Evidence reason codes exist (`decision_plane.rs:440-444`: `conformal.coverage.valid/violation`, `conformal.calibration.updated`) but I found no emission of them from the searcher path I read.

**Tests.** `conformal.rs:487-904` (~40 unit tests: input validation, monotonicity, serde rejection, held-out coverage `:576-591` on a uniform-rank law, Mondrian fallback `:624-639`, NaN defense `:841-858`, state-preservation-on-error `:864-902`). Integration: `frankensearch/tests/cross_component.rs:1170-1239`.

**Status.** Real library code; **dormant in production**: `with_conformal_calibration` / `with_adaptive_conformal_state` have zero callers outside `searcher.rs` (grep), so no runtime constructs a calibration. The interaction-lane/oracle files reference "conformal" only as toggles and invariant names (`interaction_lanes.rs`, `interaction_oracles.rs`).

**Candidate Cairn home.** PROPORTIONAL-SCRUTINY ROUTER — the *p-value + Mondrian (per-class) calibration* pattern is the piece worth borrowing: "how surprising is this claim's score relative to a calibration set of its class" is exactly a scrutiny-allocation signal with a distribution-free meaning. Do NOT borrow the adaptive-alpha update.

**Cost.** O(n log n) calibrate, O(log n) query. Re-implementation ≈ 80 lines for split conformal + p-value + Mondrian.

**Evidence tag.** Split-conformal quantile and p-value: PROVEN-in-source (arithmetic checked; held-out coverage test exists, though only on one synthetic law). Adaptive alpha: **CONJECTURE at best — directionally inconsistent with ACI** (verified from `:425-431`, `:534-540`, `searcher.rs:2932-2935`).

**Epistemics risk.** High if borrowed wholesale: the module's docs say "distribution-free search coverage" and the reason-code vocabulary says `conformal.coverage.valid`, but the only wiring feeds a rank-correlation proxy into a non-ACI update. A reader of the evidence log would believe a coverage guarantee was being tracked. Small-n clamp silently drops validity.

---

### B.3 `crates/frankensearch-core/src/decision_plane.rs` (1612 lines) — Q4 (decision-plane half)

**Mechanism (precise).** A *types-only contract*, no evaluator. Code is `:1-840`, tests `:842-1612`. Contents: `PipelineState` (Nominal/DegradedQuality/CircuitOpen/Probing, `:56-60`, transition diagram `:46-54`), `PipelineAction` (`:84`), `LossVector {quality, latency, resource}` with `weighted_total` (non-finite → `f64::MAX`, negatives clamped, `:130-185`), `LossWeights` presets (default 0.5/0.3/0.2, LATENCY_FIRST 0.2/0.6/0.2, QUALITY_FIRST 0.7/0.1/0.2; `:194-233`), `DecisionOutcome {state, action, expected_loss, reason, query_class}` (`:240-251`), `CalibrationStatus` lifecycle Uncalibrated→Calibrating{observations,target}→Calibrated{ece,observations}→Stale{reason,…} (`:262-292`), `CalibrationThresholds` defaults min_observations 100, max_ece 0.05, drift_kl 0.1, recalibration_interval 1000 (`:337-364`), `ReasonCode` newtype with `namespace.subject.detail` validation (`:377-503`) and ~40 constants, `Severity`, `EvidenceEventType` (decision/alert/degradation/transition/replay_marker, `:546-557`), `EvidenceRecord {event_type, reason_code, reason_human, severity, pipeline_state, action?, expected_loss?, query_class?, source_component}` (`:587-606`), `ResourceBudget`/`ResourceUsage`/`ExhaustionPolicy`, `DecisionContext` (`:787-805`), and `IntegrationCriteria` — a fieldless struct anchoring six prose invariants (`:809-840`) that are "not runtime-checked".

**Correctness verdict.** Nothing to be incorrect about numerically except `weighted_total` (fine). The *expected-loss minimization* described in the module doc (`:13-18`) is not implemented here — there is no function that takes a `DecisionContext` and returns a `DecisionOutcome`. Call-site census: `DecisionContext`, `DecisionOutcome`, `LossWeights::apply`, `weighted_total` have **no production constructors/callers** outside this file (grep). What IS load-bearing is the evidence vocabulary: `EvidenceRecord::new` + `ReasonCode` constants are used by `fusion/src/circuit_breaker.rs` (6 sites), `fusion/src/phase_gate.rs:253-261, 365-374`, and `fsfs/src/evidence.rs:850`.

**Evidence ledger shape.** The JSONL envelope (`schemas/evidence-jsonl-v1.schema.json`) is `{v:1, ts, event{event_id: ULID, type, project_key, instance_id, trace{root_request_id, parent_event_id}, reason{code, human, severity}, replay{mode, seed?, tick_ms?, frame_seq?}, redaction, payload}}`. Linkage is **causal by ULID** (`parent_event_id`), not hash-chained: no `prev_hash`/digest field exists (grep of the schema returns only `query_hash`/`hash_sha256` redaction options). `fsfs/src/evidence.rs:11-17, 54-78` confirms "chain of evidence events linked by correlation", i.e. trace links. So this is an **append-only decision log with reason codes and replay seeds**, not a tamper-evident ledger.

**Decision it drives.** None directly. It is the shared vocabulary for the adaptive components' logs.

**Tests.** `decision_plane.rs:849-1612` — serde round-trips, display strings, `all_reason_code_constants_are_valid` (`:1080`), `weighted_total` edge cases (`:1571-1601`). No test of any decision logic (there is none).

**Status.** Real as a contract; the loss-minimization half is **aspirational/vestigial**; the evidence-record half is load-bearing.

**Candidate Cairn home.** CLAIMS DB / SELECTOR AUDIT — the *ReasonCode discipline* (a closed, validated `namespace.subject.detail` vocabulary; "ad-hoc string codes are forbidden", `:823-824`) and the `replay{mode, seed, frame_seq}` block are cheap and directly useful for an auditable selector log. The loss-vector scaffolding is homeless (nothing computes it).

**Cost.** Trivial.

**Evidence tag.** STRONG-EMPIRICAL for "this vocabulary is consumed" (three consumers read); the expected-loss model is CONJECTURE/unimplemented.

**Epistemics risk.** The module doc promises "expected-loss minimization" and an "Evidence Ledger"; neither word is delivered as a reader would assume (no evaluator; no tamper-evidence). Borrow the vocabulary, not the promise.

**Adjacent (out of my file list, but the only concrete "decision with a logged guarantee" consumer):** `fusion/src/phase_gate.rs` — an "anytime-valid e-process" gate. Its per-observation e-factor is `1+min(δ,1)` if quality beats fast, `1/(1+min(|δ|,1))` otherwise, ×1.5/×0.7 on user signal, clamped to [0.01,100] (`phase_gate.rs:311-336`, `:189-193`). Under the stated H0 "scores exchangeable" this is **not** an e-variable: for a symmetric δ of magnitude d, `E[factor] = 1 + d²/(2(1+d)) > 1`, so Ville's inequality does not apply and the `1/α` threshold (`:204-210`) does not give the claimed error control; the "inverse decision" uses `1/e_value` (`:214-216`), which is not an e-process for the reverse hypothesis either. Also opt-in only (`searcher.rs:609-617`; no other production caller found). I flag it because the parent's Q1/Q6 e-process audit should not assume frankensearch's gate is a correct reference implementation.

---

### B.4 `crates/frankensearch-core/src/canonicalize.rs` (1410 lines) — Q5 (text half)

**Mechanism (precise).** A *text* canonicalizer for embedding input, not a serialization format. `Canonicalizer` trait (`canonicalize.rs:45-54`); `DefaultCanonicalizer { max_length: 2000, code_head_lines: 20, code_tail_lines: 10 }` (`:60-77`). Pipeline (`:99-115`): (1) NFC normalization with an ASCII fast path that borrows (`:87-97`), (2) markdown stripping + fenced-code collapsing to head 20/tail 10 lines (`:127`), (3) whitespace collapse, (4) low-signal filter — a fixed list of ack phrases ("ok", "done.", "thanks", … `:23-39`) maps the whole document to the empty string, (5) truncate to `max_length` chars. Queries: NFC + trim + truncate only (`:117-122`).

**Hashing.** None in this file. The canonical text is hashed downstream by `frankensearch-storage/src/content_hash.rs:19-22` — `ContentHasher::hash(canonical_text) = SHA-256(bytes)` — and used for dedup in the ingest pipeline (`storage/src/pipeline.rs:306, 333-336, 364`). So the content address of a document is `SHA-256(DefaultCanonicalizer::canonicalize(text))`. No domain separation, no version tag in the hash input.

**Version stability.** Not version-stable by construction: any change to the markdown-stripping rules, the low-signal list, `max_length`, or the code-collapse window changes every content hash, with no schema tag to detect it. The file's own comment calls NFC "critical for hash stability" (`:101`), which is true but only for the Unicode half. The many `*_slow`/`*_bench` twins (`:280, 775, 847, 863`) plus tests like `truncate_to_chars_matches_slow` (`:881`), `normalize_whitespace_matches_slow` (`:948`) are equivalence tests between fast and reference paths — good for refactor safety, not for cross-version stability.

**Decision it drives.** Whether a document is re-embedded (hash changed), skipped (hash equal), or skipped as empty (`pipeline.rs:307-328`).

**Tests.** `canonicalize.rs:881-1400` (~45 tests: NFC, each markdown construct, code-block collapse, low-signal, truncation at char boundary, emoji preserved, unbalanced links).

**Status.** Real, load-bearing (storage pipeline, fsfs runtime, fusion queue — `pipeline.rs:227`, `runtime.rs:1803`, `queue.rs:198`).

**Candidate Cairn home.** NONE as-is. For Cairn's SUBSTRATE the lesson is negative: a lossy, rule-heavy text canonicalizer is the wrong thing to content-address *claims* by; if Cairn hashes prose, it should hash the exact bytes (or NFC only) and keep any semantic normalization out of the address.

**Cost.** Linear in text; trivial to re-implement if wanted.

**Evidence tag.** STRONG-EMPIRICAL (behavior verified by reading; tests seen; no formal property).

**Epistemics risk.** Low for search, high if mistaken for a canonical form: two different source texts can share a hash (e.g. differing only in stripped markdown or beyond char 2000), and the same text changes hash across canonicalizer versions.

---

### B.5 `crates/frankensearch-core/src/generation.rs` (8367 lines) — Q5 (serialization+hash half)

**Mechanism (precise).** Two distinct hashing regimes coexist:

(a) **Typed canonical encoding + SHA-256 with domain separation.** `CanonicalEncoder` (`generation.rs:3396-3449`): starts with a length-prefixed domain tag (`new(domain)` → `bytes(domain)`, `:3401-3405`); integers big-endian (`u16/u32/u64`, `:3411-3421`); `usize` widened to u64 (`:3423-3425`); byte strings and text are **length-prefixed** (`:3427-3434`); `Option` is a 1-byte presence tag (`:3436-3444`). Digest = `SHA-256(encoder.finish())`, hex lowercased (`sha256_hex`, `:3547-3554`). Every identity type has its own domain string and a `schema_version` field that is itself encoded first, e.g. `b"frankensearch.artifact-generation-identity.v1"` (`:145-150`), `b"frankensearch.embedding-space.v1"` (`:2008-2041`, with artifact list sorted by role before encoding, `:2018-2019`), `b"frankensearch.generation.canonical-ordered-docset.v1"` (`:4236-4237`, used by `CanonicalDocsetV1::digest`, `:4340-4349`), `b"frankensearch.generation.source-checkpoint.v1"` (`:4599-4600`, `SourceCheckpointV1::derive(commit_range)`, `:4648-4655`, with no `from_bytes` escape hatch by design, `:4644-4646`), `b"frankensearch.generation.exact-components.v1"` (`composite_digest`, `:4578-4589`). There is also a bounds-first `CanonicalDecoder` for the activation-manifest codec (`:3451-3462`) that rejects non-canonical forms.

(b) **`GenerationManifest.manifest_hash`** (`:3745-3773`): `compute_manifest_hash` clones the manifest, clears `manifest_hash`, `serde_json::to_vec`s the struct, SHA-256, lowercase hex (`:3873-3882`). Stability rests on serde field order + `BTreeMap` for maps; the manifest contains an `f64` (`RepairDescriptor.overhead_ratio`, `:3689`), so hash equality depends on serde_json's float formatting — stable within Rust/serde_json, **not** a language-neutral canonical JSON (no RFC 8785). Comparison is case-insensitive (test `:7226-7228`).

**Correctness verdict.** Regime (a) is a sound content-addressing scheme: domain-separated, length-prefixed, fixed-endian, schema-versioned, and tested for field sensitivity (`every_artifact_generation_field_changes_the_fingerprint`, `:6018-6033`; `every_identity_field_participates_in_the_bundle_fingerprint`, `:6601`), canonical ordering (`artifact_role_order_is_canonical_but_duplicate_roles_fail`, `:6920`), domain distinctness (`the_checkpoint_domain_is_distinct_from_the_docset_domain`, `:8098`; `the_canonical_domain_is_distinct_from_the_fsvi_domain`, `:7836`), mutation separation (`canonical_docset_digest_separates_every_enumerated_mutation`, `:7706`), and non-canonical rejection (`:5658`, `:5784`, `:6974`). Regime (b) is adequate within one codebase, weaker than (a). 109 `#[test]` in the file.

**Decision it drives.** Generation activation/admission: a replica activates a generation only if every component receipt (exact bytes sha256 + docset digest + source checkpoint, `ExactComponentReceiptV1`, `:4361-4372`) agrees; drift is rejected "on the correct role". Consumer: `frankensearch-core/src/activation.rs` (core-internal; I found no product crate consuming activation — `rg` over `-g '*.rs'` for activation types outside core returned only `core/src/lib.rs`).

**Status.** Real, heavily tested, **core-internal** (no product consumer found at v1.6.0).

**Candidate Cairn home.** SUBSTRATE — borrow regime (a) exactly: a ~50-line `CanonicalEncoder` (domain tag, length prefixes, BE ints, Option tag) + SHA-256 (or BLAKE3) + per-type domain strings carrying `.vN`, with a field-sensitivity test per addressed type. This is the cleanest reusable thing in Part B.

**Cost.** Trivial to re-implement; negligible runtime.

**Evidence tag.** PROVEN-in-source for regime (a) (encoder read; domain/field-sensitivity tests read). STRONG-EMPIRICAL for regime (b).

**Epistemics risk.** Two regimes in one file invite using the serde_json one where the typed one is meant. Cairn should have exactly one.

---

### B.6 `crates/frankensearch-index/src/generation_root.rs` (14028 lines) — Q5 (filesystem half)

**Mechanism (precise).** Descriptor-owned admission of an on-disk generation root: qualifies a private root directory on an allow-listed local filesystem (Linux ext4/Btrfs, Apple-Silicon APFS via pre-opened fds; everything else `UnsupportedPlatform`, `generation_root.rs:10-21`), admits immutable files against an exact `GenerationFileExpectation { byte_len, sha256: Option<[u8;32]>, role }` (`:640-708`; immutable artifacts require a sha256, `:654-660`; control anchors may be length-only, `:673-675`), hashes by `pread` in 64 KiB chunks up to the expected length with a hard ceiling (`:3870-3895`, `GENERATION_ROOT_MAX_FILE_BYTES` = 16 GiB, `:83`), exposes fsync barriers and non-blocking `flock` guards, and binds capabilities to the creating process (fork → `ForkedProcess`). Mount identity digests are domain-separated too (`b"frankensearch.generation-root.linux-namespace.v2"`, `:5589-5590`; `…macos-mount.v1`, `:6117-6118`). `#![forbid(unsafe_code)]` (`:70`).

**Correctness verdict.** Not audited line-by-line (14k lines, mostly platform plumbing); the hashing loop and expectation types read as fail-closed. 151 `#[test]`.

**Decision it drives.** Whether a generation's files are admitted for serving. 

**Status.** Real, but **no consumer anywhere in the repo** beyond a re-export in `frankensearch-durability/src/lib.rs:43` (grep incl. tests/benches). Substrate-in-waiting.

**Candidate Cairn home.** NONE (over-engineered for Cairn's scale). The one idea worth keeping: "admit by (exact byte length, sha256) pair, never by path", which is already implied by B.5.

**Cost.** Very high to port; irrelevant.

**Evidence tag.** STRONG-EMPIRICAL (read headers, expectation types, hash loop; did not audit the platform code).

**Epistemics risk.** None for Cairn unless someone is tempted to depend on it.

---

### B.7 `crates/frankensearch-core/src/recovery_plan.rs` (5402 lines, skimmed) — context only

Typed, exhaustive, pure planner from `SemanticReadiness × RequestMode × RecoveryPolicy` → `RecoveryAction` with truthfulness invariants (installing a model never claims searchable; explicit semantic requests fail closed; serialized plans are untrusted and must be re-planned, `recovery_plan.rs:10-38`). Schema `frankensearch.recovery_plan.v4` (`:145`). 34 tests. Consumers: only `core/src/lib.rs` re-export and `core/src/types.rs` (`:26, 310`). Status: real, core-only, no product consumer. Candidate Cairn home: NONE directly; the "serialized plan is untrusted — revalidate against independently obtained state" stance (`:30-33`) is a good norm for Cairn's CLAIMS DB (a stored verdict is not a verdict until re-derived).

---

### B.8 Part-B one-line table

| File | Mechanism | Status | Cairn home | Tag |
|---|---|---|---|---|
| `frankensearch-index/src/recall_certificate.rs` | split-conformal per-query recall LCB (`floor(α(n+1))`-th order stat, trivial 0.0 when n small) + Hoeffding + empirical-Bernstein mean LCB; lazy min-ef sweep | real, tested; wired only to a bench (`benches/real_embed_ann.rs:180`) | CALIBRATION LAYER (gate *shape*), NOT a substrate proof object | PROVEN-in-source |
| `frankensearch-fusion/src/conformal.rs` | split-conformal `required_k = ⌈(n+1)(1−α)⌉`-th rank, conformal p-value `(#≥+1)/(n+1)`, Mondrian per-class; "adaptive α" = EMA toward observed error (not ACI) | real, tested; dormant (no caller of `with_conformal_calibration`) | PROPORTIONAL-SCRUTINY ROUTER (p-value + Mondrian only) | PROVEN-in-source (quantile/p-value); CONJECTURE/wrong-direction (adaptive α) |
| `frankensearch-core/src/decision_plane.rs` | types-only contract: state/action enums, LossVector, CalibrationStatus lifecycle, validated ReasonCode vocabulary, EvidenceRecord; no evaluator | real vocabulary; loss-minimization half unimplemented | CLAIMS DB / SELECTOR AUDIT (reason-code discipline + replay seed) | STRONG-EMPIRICAL (vocab consumed); CONJECTURE (loss model) |
| `frankensearch-core/src/canonicalize.rs` | NFC + markdown strip + code collapse + whitespace + low-signal filter + truncate(2000); hashed downstream by `SHA-256` for dedup | real, load-bearing | NONE (negative lesson: don't address claims by lossy canonical text) | STRONG-EMPIRICAL |
| `frankensearch-core/src/generation.rs` | `CanonicalEncoder` (domain tag, length-prefixed, BE ints, Option tag) + SHA-256 per-type fingerprints with `.vN` domains; plus serde_json-based `manifest_hash` | real, 109 tests, core-internal | SUBSTRATE (re-implement the typed encoder + domain strings) | PROVEN-in-source (typed regime); STRONG-EMPIRICAL (manifest_hash) |
| `frankensearch-index/src/generation_root.rs` | fail-closed filesystem admission by (byte_len, sha256) expectation; platform/fd/flock plumbing | real, 151 tests, zero consumers | NONE (over-engineered) | STRONG-EMPIRICAL |
| `frankensearch-core/src/recovery_plan.rs` (skim) | exhaustive readiness→action planner; serialized plans untrusted | real, core-only | NONE (norm only) | STRONG-EMPIRICAL |

## Part C — frankenfs (Q6)

Repo: `frankenfs` @ `77b0a032b9f0a11195eae002cb96f3d297e65253` (`git describe` → `v0.2.0`). All paths below are relative to `repos/frankenfs/`. Only lines actually printed are cited.

### C.0 Headline: there is no e-process in frankenfs v0.2.0

`/opt/homebrew/bin/rg -n -i 'eprocess|e_process|e-process|wealth|ville|martingale|supermartingale|e-value|sprt|anytime|likelihood-ratio|betting'` over every `.rs` file (excluding `target/`, `vendor/`) returns **zero** statistical hits. The only matches in the two named files are English words: `crates/ffs-repair/src/pipeline.rs:338` / `:5398` ("…before_processing") and `crates/ffs-harness/src/mounted_recovery_matrix.rs:325` / `:505` (`validate_process_control`, a signal-safety check). `git log --grep` for e-process terms is empty.

Where the label comes from:
- `COMPREHENSIVE_SPEC_FOR_FRANKENSQLITE_V1.md` (a sibling project's spec checked into this repo) describes e-process invariant monitors and imports `asupersync::lab::oracle::eprocess::{EProcess, EProcessConfig}` (lines 3526-3558, 3997-4231 of that file). That is the frankensqlite design, not frankenfs code.
- The real e-process implementation lives in `repos/asupersync/src/lab/oracle/eprocess.rs` (header 1-60: `e_t = E_{t-1} × (1 + λ(X_t − p0))`, Ville threshold `1/α`; `observe()` at 222-256 with factor clamp `max(1e-15)` and `max_evalue` cap). Out of scope for Part C; frankenfs crates never import it (`rg 'oracle|EProcess' crates/` → only unrelated `cross_oracle_arbitration.rs`). The parent should evaluate that file if an anytime-valid gate is wanted.
- frankenfs's own spec, `COMPREHENSIVE_SPEC_FOR_FRANKENFS_V1.md` §3.11 ("Durability Autopilot (Bayesian Expected-Loss)", lines 692-766), specifies a **Beta posterior + Chernoff bound + expected-loss argmin**, and lists the pipeline test `adaptive_policy_switches_eager_based_on_posterior` (line 6154-6169). No e-process is promised for frankenfs.

So Q6's real subject is the **Bayesian durability autopilot** and the **adaptive refresh policy** it feeds. That is what is reviewed below, plus the loss-matrix `decision.rs` and the (irrelevant) recovery-matrix validator.

### C.1 `crates/ffs-repair/src/autopilot.rs` — `DurabilityAutopilot` (Beta-Binomial expected-loss overhead chooser)

**Mechanism (precise).**
- State: Beta posterior over per-block corruption probability `p`; default prior `alpha = 1.0, beta = 100.0` (mean ≈ 0.0099) (`autopilot.rs:112-124`). Cost model: `data_loss_cost = 1e6`, `storage_cost = 1.0`, overhead search range `[0.03, 0.10]`, `metadata_multiplier = 2.0` (`:12-21`).
- Update: conjugate, per scrub observation: `alpha += min(corrupted, checked)`, `beta += checked − corrupted`; `checked == 0` is a no-op (`:133-143`). No forgetting, no reset, no windowing: the posterior accumulates for the life of the struct.
- Point estimate: `posterior_mean = alpha/(alpha+beta)` via an overflow-safe ratio (`:145-149`, helper `positive_ratio` `:48-62`).
- Risk: `risk_bound(overhead, n) = P(K > floor(n·overhead))` with `K ~ BetaBinomial(n, alpha, beta)` (`:157-173`), computed exactly in log space by the pmf ratio recurrence `P(k+1)/P(k) = (n−k)/(k+1) · (k+alpha)/(n−k−1+beta)` and normalized by the running total (`:332-366`). I checked the recurrence: `B(a+1,b−1)/B(a,b) = a/(b−1)` with `a = k+alpha, b = n−k+beta` gives exactly `(k+alpha)/(n−k−1+beta)`. Correct.
- Objective: `E[loss](o) = storage_cost·o + loss_cost·risk_bound(o, n)`; argmin by a 0.001-step grid over `[min_overhead, max_overhead]`, short-circuit to `max_overhead` when `posterior_mean >= max_overhead` (`:177-260`). Metadata groups use `loss_cost × 2` (`:200-224`).
- Output record `OverheadDecision {overhead_ratio, corruption_posterior, posterior_alpha, posterior_beta, risk_bound, expected_loss, symbols_selected, metadata_group}` (`:73-92`, built at `:262-292`).

**Correctness verdict.** Sound as Bayesian decision theory; **not** an e-process and carries **no** type-I / anytime guarantee. Nonnegativity and `[0,1]` range of mean, risk bound and tail are property-tested (`:941-1000`). Monotonicity of chosen overhead in corruption rate is property-tested up to one grid step (`:914-936`). Weaknesses: (i) prior `Beta(1,100)` encodes "1% corruption" and becomes immovable after ~10^5 clean blocks, so a disk that goes bad late is under-reacted to (no forgetting); (ii) the risk bound treats every block's corruption as exchangeable and ignores RaptorQ decode overhead, so it is a modeling approximation, not a bound; (iii) the optimizer is a flat grid, fine at 70 steps.

**Decision it drives.** Overhead ratio / repair-symbol count per block group; consumed by `pipeline.rs` (C.2).

**Tests.** Unit: `autopilot.rs:742-749` (`posterior_update_tracks_counts`: α=11, β=1090 after (10, 1000)), `:751-757`, `:759-776`, `:778-790`, `:792-801`, `:808-827`; proptests `:914-1000+` (monotonicity, unit-interval, zero-at-full-overhead, tail monotone in cutoff).

**Status.** REAL and tested as a library; **production-unwired** (see C.2). **Home:** SELECTOR AUDIT. **Cost:** ~100 lines; `O(n)` per tail × 70 grid points per (group size, metadata) key, cached per scrub. **Tag:** PROVEN-in-source (math verified, tests read). **Epistemics risk:** medium: a point-estimate posterior without forgetting can be confidently wrong after a regime change, and nothing in the record says how stale the prior is.

### C.2 `crates/ffs-repair/src/pipeline.rs` — adaptive refresh policy (the "e-process part" that is not one)

**Mechanism.**
- `RefreshPolicy::Adaptive { risk_threshold, max_staleness }` alongside `Eager`, `Lazy`, `Hybrid` (`pipeline.rs:58-81`); refresh-mode enum includes `AdaptiveEagerWrite` / `AdaptiveLazyScrub` (`:84-99`).
- Autopilot is opt-in via builder `with_adaptive_overhead(DurabilityAutopilot)` (`:914-919`); per-group policy via `with_group_refresh_policy` (`:931-953`).
- `update_adaptive_policy(&ScrubReport)` (`:1552-1647`): clears the per-group decision map, returns early if no autopilot, feeds `(blocks_corrupt, blocks_scanned)` of that scrub into the posterior (`:1566`), computes one `OverheadDecision` per `(source_block_count, metadata_group)` key (`:1577-1584`), clamps `symbols_selected` to the layout's repair capacity and recomputes risk/loss (`:1586-1607`), appends a `PolicyDecision` evidence record carrying posterior α/β, overhead, risk bound, expected loss, `decision: "adaptive_overhead_expected_loss"` to the JSONL ledger (`:1621-1644`; record ctor `evidence.rs:590-594`, schema `evidence.rs:150-175`). Called after a full scrub (`:1161`) and after a per-group scrub (`:1261`), so the posterior is filesystem-wide but updated per group.
- On a group write or scrub, the refresh gate reads the cached decision (`:1405`); for `Adaptive` it takes `posterior = decision.corruption_posterior`, falling back to the live autopilot mean, falling back to **0.0** when no autopilot is attached (`:1444-1450`); if `posterior >= risk_threshold` → eager refresh on write (else lazy-on-scrub), otherwise write-path refresh only when `dirty_age >= max_staleness` (`:1460-1482`). Block-count override can still force refresh (`:1524-1530`).

**Correctness verdict.** The gate is `posterior_mean >= risk_threshold`: a **point-estimate comparison**, not the computed `risk_bound`, and not a sequential test. It is monotone and cheap, but a reader who sees "risk_threshold" may assume a tail probability is being thresholded; it is the posterior mean. Silent degradation: `Adaptive` without `with_adaptive_overhead` resolves posterior to 0.0 and behaves as `Lazy` forever (`:1444-1450`). No validity question arises because nothing claims error control. The evidence record is the good part: every decision is logged with its full posterior state.

**Decision it drives.** Eager-vs-lazy repair-symbol refresh per block group, and the refresh symbol count.

**Tests.** `pipeline.rs:4095-4159` (`adaptive_policy_switches_eager_based_on_posterior`: injects a fixture decision with posterior 0.01 → generation unchanged and group stays dirty; then 0.2 → generation +1 and group clean; note the posterior is **injected**, `:4132-4134`, `:4147-4149`, not produced by a scrub), `:4213` (`adaptive_policy_logs_decision_on_clean_scrub`), `:4261` (`adaptive_policy_controls_symbol_refresh_count`), `:4335` (`adaptive_policy_clamp_preserves_metadata_expected_loss`, calls `update_adaptive_policy` directly `:4365`).

**Status.** REAL code, tested, **not reachable from production**: the mount-time scrub daemon constructs `ScrubWithRecovery::new(...).with_repair_writes_enabled(...)` with no `with_adaptive_overhead` and no `Adaptive` policy (`crates/ffs-cli/src/main.rs:7125-7133`); `rg 'RefreshPolicy::Adaptive|with_adaptive_overhead'` outside `pipeline.rs` returns only tests. Classify as **partial (library-complete shelfware)**. **Home:** SELECTOR AUDIT (the logged `PolicyDecisionDetail` shape, not the refresh gate). **Cost:** negligible. **Tag:** STRONG-EMPIRICAL (tests exist; gate semantics weaker than the naming suggests; no production exercise). **Epistemics risk:** high if cited as "frankenfs runs Bayesian adaptive repair in production": it does not.

### C.3 `crates/ffs-core/src/lib.rs:37536-37840` — a second, divergent `DurabilityAutopilot`

**Mechanism.** `DurabilityPosterior` with prior `Beta(1,1)` (`lib.rs:37537-37548`), conjugate `observe_blocks` (`:37566-37573`), mean and variance (`:37576-37592`). `DurabilityAutopilot::choose_overhead_for_group(candidates, K)` (`:37690-37768`): `p_hi = mean + z·sd` (`:37698-37700`), per candidate ratio `r ∈ [1.03, 1.10]` with `ρ = r − 1`, risk = `1.0` if `ρ ≤ p_hi` else Chernoff `exp(−K·KL(ρ‖p_hi))` (`:37722-37733`), argmin of `redundancy_cost·ρ + corruption_cost·risk`. `RepairPolicy { overhead_ratio, eager_refresh, autopilot: Option<_> }` with `#[serde(skip)]` on `autopilot` (`:37782-37791`); `effective_overhead_for_group` queries candidates 1.03..1.10 (`:37812-37823`).

**Correctness.** Chernoff-KL upper bound on `P(Bin(K,p) ≥ ρK)` for `ρ > p` is the standard form and is implemented correctly; using `p_hi` instead of `p` is a conservative heuristic, not a posterior predictive. Prior `Beta(1,1)` here vs `Beta(1,100)` in ffs-repair: the two autopilots give different answers for the same scrub history, and nothing reconciles them. **Tests:** `lib.rs:47088-47101`, `51366+` (unit block), proptests `83591+`; `crates/ffs/src/lib.rs:26-30, 226-245`. **Status:** real, tested, production-unwired (serde-skipped; `RepairPolicy` only constructed in tests: `crates/ffs/src/lib.rs:27, 237`). **Home:** NONE (duplicate of C.1). **Tag:** STRONG-EMPIRICAL. **Risk:** two implementations with one name.

### C.4 `crates/ffs-repair/src/decision.rs` — hand-written loss matrix policy engine

**Mechanism.** `RepairState::classify(corrupted, total, io_errors)` → `Clean | MinorCorruption(<1%) | SevereCorruption | IoStall` (`decision.rs:13-40`); five `RepairAction`s (`:47-68`); a 4×5 constant loss matrix (`:79-118`); `safety_override` forces `RepairLocal` or `DegradeReadonly` when `corruption_posterior > 0.05` (`:121-140`); `select_action` = override else argmin loss (`:165-200`). **Correctness:** internally consistent; the numbers are design constants, not estimates. **Tests:** `:209-417` unit + proptests. **Callers:** none outside its own tests (`rg 'RepairState::|select_action'` over crates → only `decision.rs`). **Status:** vestigial/spec-artifact. **Home:** NONE. **Tag:** CONJECTURE. **Risk:** low; a loss table with invented units will be read as calibrated if copied.

### C.5 `crates/ffs-harness/src/mounted_recovery_matrix.rs` — not statistical

A validator for `tests/workload-matrix/mounted_recovery_matrix.json`: required filesystems, lifecycle events, classifications (`mounted_recovery_matrix.rs:11-30`), per-scenario identity / pre-crash ops / recovery command / survivors / artifact paths / process-control checks (`:318-330`); `validate_process_control` rejects unsafe signal methods and destructive host commands (`:505-540`). No posterior, no test statistic, no e-process. **Status:** real, irrelevant to Q6. **Home:** NONE. **Tag:** n/a.

### C.6 Per-file table

| File | Mechanism | Status | Cairn home | Tag |
|---|---|---|---|---|
| `ffs-repair/src/autopilot.rs` | Beta(1,100) posterior on corruption rate; exact Beta-Binomial tail; expected-loss argmin over overhead grid; full decision record | real, tested, production-unwired | SELECTOR AUDIT | PROVEN-in-source |
| `ffs-repair/src/pipeline.rs` (adaptive part) | `posterior_mean >= risk_threshold` → eager vs lazy refresh; logs `PolicyDecision` JSONL record per scrub | partial (shelfware; tests inject posteriors; not in mount path) | SELECTOR AUDIT (record shape only) | STRONG-EMPIRICAL |
| `ffs-core/src/lib.rs` autopilot | Beta(1,1) + z-score upper + Chernoff-KL bound over candidate ratios | real, tested, serde-skipped, unwired | NONE (duplicate) | STRONG-EMPIRICAL |
| `ffs-repair/src/decision.rs` | 4-state × 5-action constant loss matrix + posterior>0.05 safety override | vestigial, no callers | NONE | CONJECTURE |
| `ffs-harness/src/mounted_recovery_matrix.rs` | JSON schema validator for crash-recovery scenarios | real, irrelevant | NONE | n/a |
| (not in frankenfs) `asupersync/src/lab/oracle/eprocess.rs` | betting-martingale e-process with Ville threshold | out of scope; the actual e-process the label refers to | (parent to judge) | (unreviewed) |

### C.7 Takeaways for the parent synthesis

1. The "frankenfs e-process" does not exist at v0.2.0; the spec that mentions e-processes is frankensqlite's, and the code is asupersync's. Do not cite frankenfs as an e-process precedent.
2. The reusable piece is the **logged Bayesian decision record**: `{posterior_alpha, posterior_beta, posterior_mean, risk_bound, expected_loss, decision}` appended to an append-only ledger on every decision (`pipeline.rs:1621-1644`, `evidence.rs:150-175`). For Cairn's SELECTOR AUDIT, a Beta posterior over "greenlit problem panned out" plus that record shape is ~50 lines and gives an auditable trail. It is a posterior, not a guarantee; pair it with the asupersync-style e-process if a stopping rule with error control is required.
3. Misuse risk: thresholding a posterior **mean** (as `pipeline.rs:1460` does) while calling the knob `risk_threshold`; and an unbounded-memory prior that never forgets.

## Synthesis (parent)

**Borrow — re-implement, never depend (four mechanisms).**

1. **Claim lattice + evidence envelope → CLAIMS DB** (`fgdb-claim`, `fgdb-evidence`). Each claim kind fixes the strongest class it may justify; `justify(target)` returns a typed `Justification` or `LatticeViolation`, never a bool; declared context (population, sampling rule, α, assumptions) and a deterministic fallback are mandatory; the claim class is *derived*, never a settable field. This is PROVEN / STRONG-EMPIRICAL / CONJECTURE / SPECULATION with the one rule that matters — a weaker tag may inform but never justify a stronger one — enforced by types. ≈200 lines.

2. **Binary e-process with Ville threshold → SELECTOR AUDIT, and the CALIBRATION LAYER's missing number** (`asupersync` core + fgdb wrapper). `E_t = Π(1+λ(X_t−p0))`, reject at `1/α`, peek any time, fixed window, no reset. CONJECTURE → STRONG-EMPIRICAL requires `E_t ≥ 1/α` against a *declared* null `p0`. ≈30 lines. Declare `p0` honestly; never reopen a trial after non-rejection.

3. **Split-conformal threshold + conformal p-value, Mondrian per class → PROPORTIONAL-SCRUTINY ROUTER** (asupersync quantile with the `+∞` convention; frankensearch-fusion p-value and per-class calibration). Distribution-free "how surprising is this claim for its class" with a stated false-alarm rate under exchangeability. ≈60 lines. Leave behind fgdb's realized-coverage gate, frankensearch's adaptive-α, and the TwoSided median leak.

4. **Typed canonical encoder + domain-separated hash, plus a replay-completeness lattice → SUBSTRATE** (frankensearch `CanonicalEncoder`, same shape as fgdb-evidence binding bytes; `ReplayCompleteness` meet-semilattice). Length-prefixed `.vN` domain tag, BE ints, length-prefixed bytes, Option tag, a field-sensitivity test per addressed type; grade stored work replayable / structural / verifiable-if-artifacts-supplied / audit-only. ≈200 lines.

**Not what the name says.** The frankensearch *recall certificate* is a calibration bound (`floor(α(n+1))`-th order statistic of measured recall; stores the bound, not the sample), not a verifiable proof object — it does **not** solve Cairn's succinct-certificate problem. Non-replayable work needs a *witness* checked deterministically (the factor found; for ANN, returned ids + distances + a seeded brute-force spot-check). Only its gate shape (target, α, sample, named inequality, trivial bound at small n) belongs in the CALIBRATION LAYER.

**Homeless cleverness.** fgdb's exploration budget (Hoeffding mislabeled "conformal", evaluated under optional stopping; not a bandit); `decision_plane.rs` loss vectors (no evaluator); `generation_root.rs` (14k lines, zero consumers); fgdb's 7.9k-line log codec; both frankenfs Bayesian autopilots (sound shelfware, no error control); `canonicalize.rs` (lossy text is the wrong address for claims).

**Biggest misuse risk: a name becomes a guarantee.** Across the suite "conformal", "certificate", "e-process", "risk_threshold" out-promise the code: frankensearch's phase-gate e-factor has `E[factor] > 1` under its own H0; its adaptive α moves *toward* observed error; fgdb's exploration bound peeks; frankenfs thresholds a posterior *mean*. Tags must key on the verified mechanism, never the label. Quote frankengraphdb's doctrine into Cairn's constitution: "a monitor that drives no named decision is dead code, but binding it to a decision does not make it an invariant."

**Over-engineered for Cairn's scale:** everything above the math — bit-exact replay envelopes, per-component OIDs, keyed identity authorities. Take the math and three rules (append-only, totally ordered, class derived not stored), not the 40k lines.

## Per-file table

| File | Mechanism | Status | Cairn home | Tag |
|---|---|---|---|---|
| fgdb `fgdb-calibrate/src/eprocess.rs` (+asupersync `lab/oracle/eprocess.rs`) | binary betting martingale `E_t=Π(1+λ(X−p0))`, reject at `1/α`, sticky, capped; identity-bound two-outcome policy gate | real, tested (unit + differential + simulated type-I); product-vestigial | SELECTOR AUDIT (also the calibration gate's number) | PROVEN-in-source |
| fgdb `fgdb-calibrate/src/conformal.rs` (+asupersync `lab/conformal.rs`) | split conformal; Upper: `⌈(1−α)(n+1)⌉`-th order stat, `+∞` if rank>n; TwoSided: `|v−median|`; wrapper adds realized-coverage gate, fail-closed dispositions | real, tested (unit + coverage simulation); product-vestigial | PROPORTIONAL-SCRUTINY ROUTER (Upper mode only) | PROVEN-in-source (Upper); heuristic (coverage gate) |
| fgdb `fgdb-calibrate/src/exploration.rs` (+asupersync `lab/exploration_budget.rs`) | novelty stopping rule: `p̂ + sqrt(ln(1/α)/2n) ≤ 1−coverage`; attestation-or-fallback | real; load-bearing in `fgdb-sim` campaigns | ORCHESTRATOR (attestation shape only; not a bandit) | STRONG-EMPIRICAL (eng) / CONJECTURE (1−α) |
| fgdb `fgdb-calibrate/src/log.rs` | append-only, totally ordered decision records; claim class derived, not stored; OIDs via identity authority; not hash-chained | real, tested; product-vestigial | CLAIMS DB (three rules only) | STRONG-EMPIRICAL |
| fgdb `fgdb-calibrate/tests/wrapper_identity_laws.rs` | differential bit-for-bit wrapper-vs-core laws; log order; two-identity decision contract; epoch monotonicity | real tests | CALIBRATION LAYER (test discipline) | n/a |
| fgdb `fgdb-calibrate/tests/sextant_e2e.rs` | end-to-end of all monitors under lab runtime → log → envelopes → policy-epoch promotion → sticky revert | real tests | n/a | n/a |
| fgdb `fgdb-evidence/src/lib.rs` (+`fgdb-claim`) | EvidenceEnvelope {claim, evidence_oid, policy, strata, propensity, window, epoch, fallback}; canonical binding bytes + injected hash; claim lattice `justify`; ReplayCompleteness meet-semilattice; no chain | real, tested; no product writer | CLAIMS DB (+ SUBSTRATE for completeness grades) | PROVEN-in-source |
| fgdb `fgdb-sim/src/campaign.rs` (e-process part) | no e-process; exploration-budget stop → `NotFalsified` under named sampling model | real, load-bearing | ORCHESTRATOR (claim-class discipline) | STRONG-EMPIRICAL |
| fs `frankensearch-index/src/recall_certificate.rs` | per-query recall LCB `floor(α(n+1))`-th order stat (0 if small n) + Hoeffding + empirical-Bernstein; lazy min-ef sweep; stores bounds not sample | real, tested; bench-only wiring | CALIBRATION LAYER (gate shape); NOT a substrate certificate | PROVEN-in-source |
| fs `frankensearch-fusion/src/conformal.rs` | `required_k=⌈(n+1)(1−α)⌉`-th rank (clamped, not `+∞`), p-value `(#≥+1)/(n+1)`, Mondrian; "adaptive α" EMA toward observed error | real, tested; dormant | PROPORTIONAL-SCRUTINY ROUTER (p-value + Mondrian) | PROVEN (quantile/p) / CONJECTURE (adaptive α) |
| fs `frankensearch-core/src/decision_plane.rs` | types-only: states, LossVector, CalibrationStatus, validated ReasonCode, EvidenceRecord; no evaluator; ULID-linked not hash-chained | vocabulary load-bearing; loss model unimplemented | CLAIMS DB / SELECTOR AUDIT (reason-code + replay seed) | STRONG-EMPIRICAL / CONJECTURE |
| fs `frankensearch-core/src/canonicalize.rs` | NFC + markdown strip + collapse + low-signal filter + truncate; SHA-256 downstream for dedup; not version-stable | real, load-bearing | NONE (negative lesson) | STRONG-EMPIRICAL |
| fs `frankensearch-core/src/generation.rs` | `CanonicalEncoder` (domain `.vN`, length-prefixed, BE, Option tag) + SHA-256; plus serde_json `manifest_hash` | real, 109 tests, core-internal | SUBSTRATE (typed regime) | PROVEN-in-source (typed) / STRONG-EMPIRICAL (manifest) |
| fs `frankensearch-index/src/generation_root.rs` | fail-closed fs admission by (byte_len, sha256); platform plumbing | real, 151 tests, zero consumers | NONE | STRONG-EMPIRICAL |
| fs `frankensearch-core/src/recovery_plan.rs` | readiness→action planner; serialized plans untrusted | real, core-only | NONE (norm only) | STRONG-EMPIRICAL |
| ffs `ffs-repair/src/pipeline.rs` (adaptive part) | no e-process; `posterior_mean ≥ risk_threshold` → eager/lazy refresh; logs PolicyDecision record | partial; not in mount path | SELECTOR AUDIT (record shape only) | STRONG-EMPIRICAL |
| ffs `ffs-repair/src/autopilot.rs` | Beta(1,100) posterior; exact Beta-Binomial tail; expected-loss argmin | real, tested, unwired | SELECTOR AUDIT | PROVEN-in-source |
| ffs `ffs-harness/src/mounted_recovery_matrix.rs` | JSON validator; nothing statistical | real, irrelevant | NONE | n/a |
