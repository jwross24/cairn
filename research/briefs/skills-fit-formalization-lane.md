# Brief: which disciplines of the Lean-loop skills the formalization lane adopts

Bead `cairn-9zp`. Read date 2026-09-05, repo at `a6ddc69`. Question put by the operator
(2026-09-02): should the Claude Code skills on this machine, `/lean-formal-feedback-loop`
first, shape how the F4 (`cairn-m1-cqt.5.4`, statement hasher) and F5 (`cairn-m1-cqt.5.5`,
axiom set) beads are worked. Every SKILL.md below was read in full, with the references the file list names;
each row names the Cairn file or bead it maps onto or says why it does not map. The pattern
followed is `research/briefs/language-and-agent-ergonomics.md`: a tagged brief whose rows land
only through the bead that acts on them.

Tags: **FACT** = read from the skill file or a repo file at the cited line; **INFERRED** =
a mapping this brief draws, no file states it; **ABSENCE** = looked for and not found, which
is not evidence of nothing.

Files read: `~/.claude/skills/lean-formal-feedback-loop/SKILL.md` (249 lines) and its five
references (`PROOF-ARTIFACTS.md`, `CONFORMANCE-PROCEDURE.md`, `LEAN-PATTERNS.md`,
`FROG-PRIORITY.md`, `FEEDBACK-EXAMPLES.md`, 790 lines); `testing-conformance-harnesses/SKILL.md`
(500 lines) and `references/FIXTURE-PATTERNS.md`; `research-software/SKILL.md` (212 lines) and
`references/STRATEGIES.md`, `OUTPUT-TEMPLATES.md`. Cairn side: `src/cairn/lean.py`,
`src/cairn/challenge.py`, `src/cairn/bundle.py:192-243`, `bundle/lean.json`, PLAN §7 lines
918-962 and §16 decision 13 (line 1716), `research/grounding/lean-checker-protocol.md`,
`research/grounding/lean-toolchain-pins-and-mathlib-cost.md`, `tests/goldens/PROVENANCE.md`,
the F4 and F5 bead bodies and the F5 design comment of 2026-09-02.

## 0. The answer in one paragraph

None of the three skills becomes a Cairn skill, and none is pasted as an opener section.
`/lean-formal-feedback-loop` is an execution program for one Rust repository whose Lean file
is a *model* of Rust code; its loop is keyed on artifacts Cairn does not have (coverage JSON,
`cass` history, a frog queue) and on a question Cairn does not ask (does the Rust match the
model). Cairn's Lean is the authority, not a model, so the seven-check parity pass, the
routing matrix and the Bayes bookkeeping have nothing to attach to. Four disciplines inside
it do transfer, and Cairn already carries three of them as standing rules: proof friction as
evidence (F4's "if any probe fails, redesign"), an executable witness plus a pinned test per
closed loop (`scripts/bead-test-plan.sh`, the planted negative), and a hash-carrying artifact
record (the gate run, `challenge.binding`, the bundle pin). The fourth, **one lever per
iteration**, is the one F4 gains as a bullet. `/testing-conformance-harnesses` is the better
fit for this lane because F4 *is* a conformance problem: a hasher that must agree with a
reference decision procedure (the comparator's `compareAt`). Five of its disciplines become
F4 and F5 bullets: spec pinned by revision and line range, a differential check against the
reference, golden provenance rows, a coverage matrix with explicit uncovered rows, and
fixture naming. `/research-software` contributes two: code over docs (cite the Lean source
at the pinned commit, not the manual) and stable tag over commit, which the comparator pin
in the grounding brief fails today. §5 lists the bullets as `br update` text; §6 records what
was rejected and why.

## 1. `/lean-formal-feedback-loop`

Premise (FACT, `SKILL.md:12-13, 34-41`): "treat proof friction as evidence"; hard proof
failures are "high-signal indicators of Rust defects, model drift, or theorem-scope
mismatch"; the file is "an execution program, not a theorem-writing tutorial". The loop
(FACT, `SKILL.md:20-22, 43-54`) ranks "frogs" from `formal/lean/coverage/*.json`, mines `cass` history
before ranking (`SKILL.md:56-82`, "mandatory"), attempts a proof to its first hard blocker,
classifies a route (`code-first | model-first | harness-first | theorem-first`), extracts an
executable witness, runs a seven-check conformance pass and emits a proof-carrying artifact
record. Its subject repository is asupersync, whose Lean file is a model of a Rust runtime:
`research/briefs/asupersync.md:11` records "theorems are about the Lean model … linkage to
Rust is a refinement-map document plus tests, not extraction" (FACT).

| Discipline | Where in the skill | Maps onto | Tag | Verdict |
|---|---|---|---|---|
| Proof friction as evidence: a hard blocker is data about the artifact, never "tactic debt" to push through | `SKILL.md:12-13, 39`; `LEAN-PATTERNS.md` Pattern 10 (only `tactic_debt` may be resolved without reopening the route) | F4 body step 2: "if any probe fails, the hasher's basis is wrong — record the failure and redesign … do not ship a hasher whose stability was not measured". PLAN §7:926-929 holds the closure basis at CONJECTURE for the same reason | FACT for both sides; the equivalence is INFERRED | Already Cairn's. No new bullet |
| One lever per iteration: "change one lever per iteration, then re-run" | `SKILL.md:40`; anti-pattern "changing multiple levers in one loop iteration" (`SKILL.md:230`) | F4's three probe families. A probe pair whose members differ in two edits proves nothing about either. Nothing in the F4 body requires the pair to differ in exactly one edit | INFERRED | **Adopt** as F4 bullet (§5, F4-b) |
| Executable witness plus a pinned test per closed loop | `SKILL.md:38, 50`; `PROOF-ARTIFACTS.md` "Every artifact gets a conformance test" | `scripts/bead-test-plan.sh` gates every `tests/` path a bead names; the planted-negative line in every bead's acceptance criteria; `tests/integration/test_hasher_stability.py` and `test_axiom_computation.py` are the F4/F5 witnesses by construction | FACT (CLAUDE.md working notes; bead bodies) | Already Cairn's. No new bullet |
| Proof-carrying artifact record: theorem, hash, tier, files, "no artifact, no claim" | `PROOF-ARTIFACTS.md:3, 17-48, 123-137` (`ProofWitness`, the closure record with `artifact_hash`) | `claims.GateRun` with `formal_statement_hash`, `renderer_hash`, `prelude_hash` (`src/cairn/challenge.py:121-139`); `challenge.binding` refuses an empty field (`:141-153`); the `lean_artifact` evidence node of PLAN §7:932-934; the ARTIFACTS block `.githooks/pre-commit` demands | FACT | Already Cairn's, and stricter: the skill hashes "theorem source block" text by `sed` (`PROOF-ARTIFACTS.md:50-59`), which is what F4 refuses (raw bytes carry position-dependent names, PROVEN at `research/grounding/lean-checker-protocol.md:52`) |
| `#print axioms` before emission, "must print only propext, Quot.sound, Classical.choice" | `PROOF-ARTIFACTS.md:61-66` | F5, with one inversion: the skill reads printed text; PLAN §16 decision 13 (line 1716-1722) forbids Python re-deriving a Lean verdict from printed output, so F5 runs `Lean.collectAxioms` inside a gate-owned `lake exe` and Python records structured output | FACT | The intent maps; the mechanism is the one Cairn rejects. Bullet F5-c makes the rejection observable |
| Drift gate: chronology of the Lean file against the mapped file; "if drift gate fails, previous alignment claim is stale" | `CONFORMANCE-PROCEDURE.md:92-101, 167-173`; `PROOF-ARTIFACTS.md:68-75` (`git log` mtimes) | Cairn pins by content, not by time: the renderer, prelude and lake manifest are hashed into the gate bundle (`src/cairn/bundle.py:234-243`, CLAUDE.md working note), `tests/goldens/gate_bundle_hash.golden` moves on any edit, `lean.assert_pinned` refuses a toolchain whose commit differs from `bundle/lean.json`. What is not yet pinned: the F4 hasher and the F5 axiom module themselves | FACT for the pins; the gap is INFERRED from the F4 body ("the hasher exists as a bundle object") having no observable attached | **Adopt** as F4-d and F5-d: the new Lean sources are bundle objects and the golden move is shown |
| Budgeted mode: each loop declares a proof budget, a witness budget, a rerun budget and an exhaustion action | `SKILL.md:185-194` | The lane's open cost row: `leanchecker --fresh` on a mathlib-importing module is OPEN and assigned to F4 at `research/grounding/lean-toolchain-pins-and-mathlib-cost.md:69`; PLAN §7:935-938 says M1 measures it before sizing the corpus; `lean.DEFAULT_TIMEOUT_S = 600` is the only ceiling in code | FACT | **Adopt** as F4-f and F5-f: the wall times recorded, closing the OPEN row. The budget-exhaustion routing is not adopted (see rejected) |
| Route classification of a failed proof (code-first, model-first, harness-first, theorem-first), with an asymmetric loss matrix biased to code-first | `SKILL.md:130-150`; `CONFORMANCE-PROCEDURE.md:103-115` | A failed F4 probe has four analogous causes: the hasher implementation, the closure basis, the fixture pair, the CONJECTURE's scope. The bead already demands the failure be recorded; naming which of the four failed is one more column | INFERRED | Not a bullet: it is observable only when a probe fails, and the operator's rule is to adopt only what a close can paste. Recorded here as the column the grounding row gains if step 2 refutes |
| Theorem scope contract: every theorem carries assumes / non-goals / maps-to | `LEAN-PATTERNS.md` Pattern 9 | The claim statement node and its rendered Challenge (F3), the §7 statement pre-filters (F7), the statement-level review. F4 hashes a statement; F5 checks axioms; neither authors statement text | FACT for where statements are authored | Does not map onto F4/F5. Belongs to F7 and the review checklist |
| Counterexample-carrying development: when a proof blocks, write the bad trace as a definition and a theorem that it violates the property | `LEAN-PATTERNS.md` Pattern 2 | F4's semantic-change probe and F5's three dirty fixtures are exactly planted counterexamples | FACT | Already Cairn's (every bead's planted negative) |
| Drift-resistant naming: names encode contract and scope | `LEAN-PATTERNS.md` Pattern 13 | F5's fixture modules | INFERRED | Folded into F5-a: fixtures named for the axiom they plant |
| Frog ranking, `EV_frog`, Bayes factors, `AssuranceGapMultiplier`, the seed queue | `SKILL.md:89-118`; `FROG-PRIORITY.md` | Nothing. Cairn's work order comes from `bv --robot-plan` over bead dependencies and PLAN §10's problem selection; the priors are asupersync bug families | FACT for the skill; ABSENCE of a Cairn counterpart | Ignore |
| `cass` history mining as a mandatory step | `SKILL.md:56-82` | Nothing on this lane. The operator excluded it for Cairn (session opener 2026-09-05); `cass-cm-integration.md` keeps it as a debugging aid, not a gate | FACT | Ignore |
| Seven-check conformance parity (statement, state, transition, concurrency, cancel/drain, runtime evidence, drift) | `CONFORMANCE-PROCEDURE.md:12-101` | Six of seven ask whether a Lean model matches a Rust runtime. Cairn's Lean statement is the object itself; there is no second representation to check parity against. The one that survives is drift, handled above by the bundle pin (`src/cairn/bundle.py:234-243`) | FACT | Ignore, with the drift check absorbed by the bundle pin |
| Stuck-proof elicitation and the "galaxy-brain" prompt | `SKILL.md:157-162`; `FEEDBACK-EXAMPLES.md:125-164` | Nothing. F4 and F5 write programs against a known API; they prove no theorems | FACT | Ignore |
| Quality gates: `lake build`, `cargo test`, `clippy`, `fmt` | `SKILL.md:196-213` | `scripts/check.sh` is the single definition of green; the Lean tests inside it (`tests/unit/test_lean_pins.py`, `tests/integration/test_lean_toolchain.py`, `test_challenge_compile.py`) run one build and one fresh replay | FACT | Already Cairn's |

Verdict for the skill as a whole: **ignore as a program; adopt two disciplines as bullets**
(one lever per probe; the bundle pin on the new Lean sources) **and record one as a
grounding-row column** (route of a failed probe). Not adapted into a Cairn skill: its loop is
keyed on artifacts Cairn does not produce and its subject is Rust runtime defects.

## 2. `/testing-conformance-harnesses`

Premise (FACT, `SKILL.md:20-24`): "specifications aren't suggestions, they're contracts"; a
harness mechanically verifies every MUST/SHOULD clause; "if it's not tested, it's not
conformant". The eight-step loop (`SKILL.md:26-37`): identify the spec, extract requirements,
generate fixtures from the reference, build the harness, cover, document divergences, emit a
matrix, maintain with diff review. F4 fits the decision tree's first branch (`SKILL.md:52-59`):
"reference implementation exists → differential testing … compare outputs".

| Discipline | Where in the skill | Maps onto | Tag | Verdict |
|---|---|---|---|---|
| Identify and version-pin the specification | `SKILL.md:29, 471` ("specification source identified and version pinned") | F4's spec is `Compare.lean` in `leanprover/comparator`: `compareAt` at lines 37-59 and 67-87 of rev `5756749` (`research/grounding/lean-checker-protocol.md:52`). The ergonomics brief §7 (`research/briefs/language-and-agent-ergonomics.md:221-222`) assigns F4 "reads `Compare.lean` before hashing" and leaves open whether `compareAt` is structural equality on `ConstantVal`; F4-a is what makes the bead demand the answer. No F4 bullet requires the answer to be written down with its line range | FACT for the sources; the gap is INFERRED | **Adopt** as F4-a |
| Differential testing against the reference | `SKILL.md:52-59, 87-160` | The comparator runs on macOS under the comparator clone's own `scripts/fake-landrun.sh` in 2.3-6.6 s per case with the closure compare unaffected by the missing sandbox (`research/grounding/lean-checker-protocol.md:22, 32`). On F4's three probe pairs the comparator is an oracle for the hash: hash-equal pairs must be "okay", the semantic pair must mismatch. This is the cheapest evidence that the CONJECTURE's basis is the comparator's basis, and it is not F6 (the comparator as a *gate*, pinned in the bundle with an external kernel); here it is a scratch build used once as a reference | INFERRED | **Adopt** as F4-c |
| Golden files with an `UPDATE_GOLDENS` workflow and diff review | `SKILL.md:162-211` | `tests/goldens/PROVENANCE.md:3` documents the same workflow (`UPDATE_GOLDENS=1 uv run pytest …`) and `tests/unit/test_golden_harness.py` exists | FACT | Already Cairn's |
| Fixture provenance: generator, tool versions, regeneration command, date | `SKILL.md:406-426`; `FIXTURE-PATTERNS.md:28-58` | `tests/goldens/PROVENANCE.md` carries a row per golden with a volatility grade. F4's canonicalization known-answer vector and F5's expected-axiom table are new goldens with no row yet | FACT | **Adopt** as F4-e and F5-b |
| Coverage matrix: enumerate every clause, show which are tested, never ship unknown gaps | `SKILL.md:39-48`; anti-pattern "incomplete COVERAGE.md" | PLAN §7:948-950 enumerates what the allow-list rejects: `sorryAx`, the per-computation axioms of `decide +native` and `bv_decide`, any custom axiom. The F5 body plants three dirty modules and omits `bv_decide`. A clause with no fixture is today invisible | FACT for the clause list; the gap is INFERRED | **Adopt** as F5-a |
| `DISCREPANCIES.md`: every intentional divergence from the reference, with a reason and a review date | `SKILL.md:374-404` | F4's hasher deliberately excludes the target's value (`research/grounding/lean-checker-protocol.md:52`) and may canonicalize differently from `compareAt`'s traversal order. Those are divergences from the reference to be listed, not a separate file: the grounding row is the place | INFERRED | Folded into F4-a |
| XFAIL, never SKIP, for a known divergence | `SKILL.md:402, 463, 476` | Cairn's one Lean skip is environmental (`tests/integration/test_challenge_compile.py` skips the mathlib-prelude compile where `lean/.lake/packages/mathlib` is absent, with a printed reason) and every other Lean test runs everywhere. No known-divergence skip exists to convert | FACT | Already Cairn's; nothing to adopt |
| Test error cases, not only happy paths | `SKILL.md:464, 479` | F5's three refusals and the bundle-config mismatch; F4's planted negative (raw export bytes diverge across builds) | FACT | Already Cairn's |
| Round-trip conformance | `SKILL.md:213` | No serialization on this lane beyond canonical bytes, which `tests/vectors/canon_kat.json` already pins | FACT | Does not apply |
| Process-based conformance with an external runner | `SKILL.md:355` | The comparator as a gate, with `landrun` and an external kernel: bead F6, gold tier, inside the F2 container | FACT | Maps onto F6, not F4/F5 |
| Compliance report generated automatically | `SKILL.md:428-453` | Nothing on this lane. The close comment's pasted table is the report for a bead; a standing report is P4 alarms territory (`cairn-m1-cqt.9`) | ABSENCE | Ignore |

Verdict for the skill: **adopt five disciplines as bullets** (spec pin with divergences,
differential oracle, provenance rows, coverage matrix, fixture naming), none as an opener
section and none as a Cairn skill. The skill's Rust harness architecture is not needed:
pytest, the goldens directory and `PROVENANCE.md` already play those parts.

## 3. `/research-software`

Premise (FACT, `SKILL.md:10`): "Latest STABLE tag (not main). Filter to 2025-2026. Code >
Docs." Source priority (`SKILL.md:97-104`): source code, then recent PRs, then issues, then
posts, then official docs. Its pipeline clones to `/tmp`, checks out the latest stable tag,
spawns explorer subagents and cites `repo@commit`.

| Discipline | Where in the skill | Maps onto | Tag | Verdict |
|---|---|---|---|---|
| Stable tag, not `main` | `SKILL.md:10, 62-64, 115` | The comparator is pinned at commit `5756749` (2026-08-19) in `research/grounding/lean-checker-protocol.md:3`. Checked 2026-09-05 with `gh api`: `leanprover/comparator` carries 26 tags named for Lean releases; `v4.34.0-rc1` is `011e9d3` (2026-08-10), `v4.34.0-rc2` is `19e111e` (2026-08-21); `5756749` is 9 commits ahead of the rc1 tag, 0 behind, and its `lean-toolchain` is still `v4.34.0-rc1`. So the grounding pin is a mid-stream commit on the right toolchain, not the tag | FACT (commands above) | **Adopt** as F4-a's second clause: the F4 close names the tag or names the commit and lists the 9 commits between them |
| Code over docs: read the source at the pinned revision, not the manual | `SKILL.md:10, 117` ("Trusting docs over code … check actual defaults in source") | The F5 design comment carries a REPORTED claim (from 4.23.0 `collectAxioms` follows axioms referenced by axioms, so `native_decide` lists `Lean.trustCompiler`) that the 2026-08-21 probe did not reproduce (`decide +native` gave `[t._native.decide.ax_1_1]`, `research/grounding/lean-checker-protocol.md:43`). The lean4 source at commit `3447a66` settles it | FACT for the conflict | **Adopt** as F5-b (observed names, not assumed) and F4-g / F5-e (every Lean API cited at file:line in lean4 `@3447a66`) |
| Cite `repo@commit`, PR numbers | `SKILL.md:92` | The grounding briefs (`research/grounding/*.md`) already cite `@sha` and file:line throughout | FACT | Already Cairn's |
| Detect context first (existing pins in the project) | `SKILL.md:56-59` | `bundle/lean.json` and `lean/lake-manifest.json` are the pins; `tests/unit/test_lean_pins.py` asserts they agree | FACT | Already Cairn's |
| Settle maintenance state from commit and tag dates | `SKILL.md:69-73` (recent PRs, issues), `STRATEGIES.md` "Version Detection" | F2 (`cairn-m1-cqt.5.2`): the landrun maintenance claim is an open question the ergonomics brief §5 assigns to F2 "from commit dates". Not an F4/F5 bullet | FACT | Maps onto F2; recorded, not adopted here |
| Clone to `/tmp`, clean up after | `SKILL.md:62-64, 78` | Cairn uses the session scratchpad (`mktemp -d`, CLAUDE.md working note) | FACT | Cairn's convention differs; ignore |
| Subagent split (Sonnet code investigator, Haiku web) | `SKILL.md:182-202` | The operator's rule for this repo (`research/SESSION-PROMPTS.md`, session opener) is Opus for every audit subagent, set explicitly; research gathering is the writer's own read | FACT (session opener) | Ignore |
| Web search filtered to 2025-2026 | `SKILL.md:10, 73-76` | The `[R#]` provenance labels of `research-first-tickets.md` already carry dates | FACT | Already Cairn's |

Verdict for the skill: **adopt two disciplines** (stable tag over commit; code at the pinned
revision over docs) **as clauses inside F4 and F5 bullets**. Not a Cairn skill: it is a
research procedure for unfamiliar tools, and the lane's tools are already grounded.

## 4. Other Lean-related skills on this machine

`ls ~/.claude/skills | grep -i -E "lean|proof|formal"` on 2026-09-05 returns only
`lean-formal-feedback-loop`. `asupersync-mega-skill` is the subject repository's own skill,
not a Lean discipline, and `research/briefs/asupersync.md` already records what that
repository's Lean lane is. **ABSENCE**: no further row.

## 5. The adopted bullets, as applied with `br update`

Each bullet names a pasted observable an F4 or F5 close can show. F4-a to F4-g are
acceptance criteria of `cairn-m1-cqt.5.4`, and F5-a to F5-f of `cairn-m1-cqt.5.5`.

### F4 (`cairn-m1-cqt.5.4`) gains

- **F4-a Spec pin and divergences** (from `/testing-conformance-harnesses` and
  `/research-software`): the grounding record names the comparator revision the hasher
  mirrors, states whether it is the tag matching the toolchain (`v4.34.0-rc1` = `011e9d3`)
  or a later commit (the current grounding pin `5756749` is 9 commits past that tag on the
  same toolchain) and, if a commit, lists those commits by subject; quotes the `Compare.lean`
  lines `compareAt` compares and answers whether that comparison is structural equality on
  `ConstantVal`; and lists every deliberate divergence of the hash basis from what
  `compareAt` compares (excluding the target's value is one) with its reason. Pasted: the
  quoted lines and the divergence list.
- **F4-b One lever per probe** (from `/lean-formal-feedback-loop`): each of the three probe
  pairs (fresh rebuild; comment or unused-declaration edit; semantic edit under the
  statement) differs in exactly one edit, and the close pastes the diff between the two
  members beside their two hashes.
- **F4-c Differential oracle** (from `/testing-conformance-harnesses`): on the same three
  probe pairs, the comparator at the revision F4-a names, built in scratch and run under
  the comparator clone's own `scripts/fake-landrun.sh`, reports okay for both hash-equal pairs and a mismatch for the
  semantic pair; the verdict lines pasted. A disagreement refutes the basis under step 2 of
  the body; it is never a reason to loosen the hash. The comparator stays a scratch reference
  here; pinning it in the bundle is F6.
- **F4-d Bundle drift** (from `/lean-formal-feedback-loop`'s drift gate, in Cairn's
  content-pinned form): the hasher's Lean source is a raw gate-bundle object beside
  `challenge_renderer`, so an edit to it moves `tests/goldens/gate_bundle_hash.golden`; the
  close shows the golden moved in the attributed commit and a test asserting the object is
  present in the bundle.
- **F4-e Provenance row** (from `/testing-conformance-harnesses`): the canonicalization
  known-answer vector has a `tests/goldens/PROVENANCE.md` row naming its generator command,
  the lean commit `3447a66`, the mathlib revision and a volatility grade; the row pasted.
- **F4-f Cost recorded** (from `/lean-formal-feedback-loop`'s budgeted mode): `time -p` wall
  times of `lake build`, the hasher `lake exe` and `leanchecker --fresh` on the
  mathlib-importing Challenge are pasted and the OPEN row at
  `research/grounding/lean-toolchain-pins-and-mathlib-cost.md:69` is closed by them; where a
  run exceeds `lean.DEFAULT_TIMEOUT_S`, the bound and the wall clock at the cut are pasted and
  the row is closed as `> N s`.
- **F4-g Code over docs** (from `/research-software`): every Lean API the hasher calls
  (`ConstantInfo`, the used-constants traversal, the environment or export entry point) is
  cited at file:line in lean4 at commit `3447a66` in the grounding row, not from the manual.

### F5 (`cairn-m1-cqt.5.5`) gains

- **F5-a Coverage matrix** (from `/testing-conformance-harnesses`): one planted fixture per
  axiom class PLAN §7 (iii) names, `sorryAx`, `decide +native`, `bv_decide` and a custom
  axiom, beside the clean module; each fixture module is named for what it plants; a class
  with no fixture appears as an explicit uncovered row with its reason, never silently. The
  table of fixture, expected class and observed axiom set is pasted.
- **F5-b Observed names, with provenance** (from `/research-software`): the expected axiom
  names are recorded as `collectAxioms` reports them on `v4.34.0-rc1`, settling whether
  `decide +native` yields only the `._native.decide.ax_` shape or also `Lean.trustCompiler`
  (the design comment's REPORTED claim against the 2026-08-21 probe); the expectation table
  gets a `tests/goldens/PROVENANCE.md` row whose volatility grade states the toolchain
  dependence. Pasted: the `collectAxioms` output per fixture and the row.
- **F5-c Authority made observable** (the inversion of `/lean-formal-feedback-loop`'s
  `#print axioms` step, under PLAN §16 decision 13): the gate-owned `lake exe` emits the axiom
  set as canonical JSON on stdout and the Python reader refuses anything else; a planted
  `#print axioms`-shaped line is refused, and the refusal is pasted.
- **F5-d Bundle drift and the pin call** (from `/lean-formal-feedback-loop`'s drift gate):
  the axiom module's Lean source is a raw gate-bundle object and `permitted_axioms` stays a
  `bundle/lean.json` field, so an edit moves `tests/goldens/gate_bundle_hash.golden` (shown
  in the attributed commit); `lean.assert_pinned(gate.lean)` runs before any compile, shown
  by the pin-mismatch fixture refusing with no `lake` spawn in the log, pasted.
- **F5-e Code over docs** (from `/research-software`): `Lean.collectAxioms` and any other
  Lean API the module calls are cited at file:line in lean4 at commit `3447a66`.
- **F5-f Cost recorded** (from `/lean-formal-feedback-loop`'s budgeted mode): the wall time
  of the axiom computation on the mathlib-importing clean fixture is pasted.

## 6. Rejected, with the reason

- The frog queue, `EV_frog`, Bayes factors and the assurance-gap multiplier: they rank Rust
  subsystems by bug prior; Cairn's ranking is bead dependencies and PLAN §10.
- `cass` mining as a mandatory step: excluded by the operator for this lane.
- The seven-check parity pass and the four-way route matrix: they compare a Lean model with a
  Rust runtime; Cairn's Lean statement has no second representation. The drift check
  survives in content-pinned form (F4-d, F5-d); the route taxonomy is a grounding-row column
  if a probe fails, not a bullet.
- Budget-exhaustion routing (split the theorem, switch route): F4 and F5 write programs; a
  program that does not finish is a defect, not a route decision. The cost *measurement*
  is kept (F4-f, F5-f).
- The `ProofWitness` record and evidence ledger JSON: the gate run, the binding and the
  ARTIFACTS block already carry those fields under a canonical hash.
- The theorem scope contract (assumes / non-goals / maps-to): statement authorship is F3, F7
  and the review, not F4/F5.
- `/testing-conformance-harnesses`'s Rust harness layout, compliance report generator and
  round-trip pattern: pytest, `tests/goldens/` and `PROVENANCE.md` already fill the roles;
  there is no serialization to round-trip beyond the canon KAT.
- `/research-software`'s `/tmp` clone, subagent tiers and web-search filters: the repo's
  scratchpad rule, the Opus-for-audits rule and the dated `[R#]` labels already cover them.

## 7. No-Claim

This brief proves what the three skills say and where each discipline lands in Cairn. It
does not prove that a discipline helps: that is shown, or not, when an F4 or F5 close pastes
the observable its bullet names. A bullet whose close carries no pasted output is a bullet
this brief got wrong, and the close should say so rather than paste around it.
