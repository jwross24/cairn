# Brief: which disciplines of `/lean-proof-mastery-with-epistemic-humility` the formalization lane adopts

Bead `cairn-lnz`. Read date 2026-09-06, repo at `c0c0026`. Question put by the operator
(2026-09-06): the skill `lean-proof-mastery-with-epistemic-humility` (jsm, Jeffrey Emanuel,
v6, skill_hash `sha256:1b027976b6694978c4fc2cd6b48f84602fcf40f41921674224afb7b8991f7ef5`,
installed at `~/.claude/skills/lean-proof-mastery-with-epistemic-humility`) is on this
machine; how does it become most useful inside Cairn, and which beads gain from it. The
pattern followed is `research/briefs/skills-fit-formalization-lane.md` (cairn-9zp): a tagged
brief whose rows land only through the bead that acts on them.

Tags: **FACT** = read from the skill file or a repo file at the cited line; **INFERRED** =
a mapping this brief draws, no file states it; **ABSENCE** = looked for and not found, which
is not evidence of nothing.

Files read in full: `SKILL.md` (190 lines), `references/EPISTEMICS.md` (122),
`references/STATEMENT-FIDELITY.md` (94), `references/TOOLS-AND-TRUST.md` (181),
`references/REVIEW-PROMPTS.md` (70), `references/RESUME-AND-ORCHESTRATION.md` (103),
`subagents/ROLES.md` (111), `NOTICE.md`, `SELF-TEST.md` (first 60 lines), the heading index
of `references/FAILURE-MODES.md` (231), `scripts/check.py` (377; argument surface and the
acceptance-module generator), `scripts/diagnose.py` (74), `scripts/bootstrap.py` (header),
`templates/example-spec.json`, `examples/README.md` (first 60 lines). Not read: the four
FERMAT references, `CREATIVE-PROOF-DEVELOPMENT.md`, `PROOF-PATTERNS.md`, `OPERATORS.md`,
`HISTORY-TO-PROOF-CRAFT.md`, `LOCALIZATION.md`, `COMPUTATION-AND-SOURCES.md`; those are proof
craft for the agent writing a Solution, and §5 names when a session loads them. Cairn side:
`src/cairn/lean.py`, `bundle/lean.json`, `lean/lakefile.toml`, `bundle/role_templates.json`,
`src/cairn/schema.sql:46,242-248`, PLAN §7 lines 918-1100, `research/SESSION-PROMPTS.md`,
the bodies of `cairn-m1-cqt.5`, `.5.4`, `.5.5`, `.5.6`, `.5.8`, `.5.9`, `.3.3`, `.6.2`,
`cairn-m2-vgh` and `cairn-9zp`.

## 0. The answer in one paragraph

The skill is the discipline Cairn's own epistemics already legislate, written for the agent
holding the keyboard while it writes Lean: eleven laws (`SKILL.md:62-84`), a working loop
(`SKILL.md:89-120`), nine bounded worker roles (`ROLES.md:30-95`), three adversarial review
prompts, fifty named failure modes, a reviewer-controlled acceptance checker and a
six-field negative-knowledge record. Eight of the eleven laws are Cairn invariants by
construction (§3 rows 1-3, 6-9), so they add no bullet; the value is in the mechanics the
skill's checker and fixtures carry and the lane's bead bodies leave unstated. Four of those
are adopted as pasted observables: a planted **kernel-replay failure** built from lean4's own
leanchecker fixtures at Cairn's pinned commit, the one gate step against which F6 and .3.3
plant nothing (§3 row 22, bullets P-6d and P-33a); a **pre-build and post-replay
fingerprint** over the gate-owned Lean inputs on the unsandboxed dev arm (row 13, P-6b); an
**empty target set fails closed** clause for the axiom step (row 20, P-5a); and a
**coverage matrix** that assigns every statement-level failure class to a pre-filter, to the
Skeptic's checklist, or to an explicit uncovered row (row 23, P-8a). The library-item bead
`.5.9` gains the proof-authoring loop itself as five bullets (rows 2, 4, 5, 10, 27; P-9a..e),
because it is the first bead where an agent writes a Solution rather than gate code. The
Skeptic's checklist (`.6.2`) gains four statement-audit items and the independence-axes item
(rows 18, 19; P-62a, P-62b). The Formalizer worker and the dead-end ledger (M2) take the
six-field negative record and a typed `proposed_statement_change`, recorded as a design
comment on `cairn-m2-vgh` (§6). The skill runs in a Mode A session on a `lean/` bead, in the
mode the bead names (§7); it never runs inside Cairn (AGENTS.md, three meanings of skill).
The skill's text is proprietary and Cairn is public under MIT, so every adoption is a
restatement in Cairn's words with a file:line citation, and the one artifact Cairn takes is
lean4's, under Apache-2.0 (§1). §8 lists what was rejected and why.

## 1. The license boundary

- FACT: `jsm show lean-proof-mastery-with-epistemic-humility` reports `License: proprietary`;
  `NOTICE.md:1-53` scopes the Apache-2.0 portions to the copied Fermat material
  (`examples/P2MUtil.lean`, marked adaptations in `examples/Proofs.lean` and five further
  example files) and the lean4 fixture the skill's own tests adapt.
- FACT: Cairn is public (`jwross24/cairn`, visibility flipped 2026-09-06) under `LICENSE`
  (MIT) at `c0c0026`.
- Rule this brief applies: a discipline is restated in Cairn's words and cited by file:line;
  quotation stops at a law's title. No skill file is copied into the tree, into
  `bundle/`, or into a role template. Where a bead needs a Lean artifact the skill also
  uses, the bead takes it from the upstream project at Cairn's pinned commit under that
  project's license, with attribution in the fixture file.
- FACT: the leanchecker fixtures live in lean4 at
  `tests/pkg/leanchecker/LeanCheckerTests/` at commit `3447a668` (Cairn's `lean_commit`,
  `bundle/lean.json`): `AddFalse.lean` (blob `158722259a006471f227606ec32242be743ef7f7`,
  342 bytes, byte-identical to the blob at the skill's cited commit `819816b2`),
  `AddFalseConstructor.lean`, `ReplaceAxiom.lean`, `QuotEq.lean`, each with an
  `.out.expected`; lean4's license is Apache-2.0 (`gh api repos/leanprover/lean4/license`).
  `AddFalse.lean` runs `run_elab` and calls `Environment.addDeclCore` with
  `doCheck := false` to add a theorem `false : False` the elaborator never checked; the
  fixture family is what `leanchecker` exists to catch.

## 2. What the skill is

- FACT (`SKILL.md:1-15`): a construct / audit-only / repair / simplify / expand / resume
  procedure for Lean proofs whose opening banner states that a theorem is exactly as proved
  as its checked derivation and that labels, done-marks, certificate strings and a checker
  written to pass add nothing. FACT (`SKILL.md:58-60`): it runs files under the project's
  pinned `lake env lean`, and demands isolation for untrusted sources.
- FACT (`EPISTEMICS.md:99-122`): three orthogonal dimensions per claim, role, disposition
  and evidence class, with `FORMALLY_CHECKED` requiring exact statement, original-to-formal
  comparison, pinned versions, transitive axiom report, disclosed trust, no admissions in the
  accepted closure and completed independent review. "Kernel accepted; semantic review
  pending" is named as a precise, useful state (`SKILL.md:130-134`).
- FACT (`TOOLS-AND-TRUST.md:69-133`, `scripts/check.py`): the acceptance checker takes a
  reviewer-pinned spec outside the candidate with its own sha256 on the command line,
  compiles listed modules into a fresh output directory, generates a control module that
  proves `((fun {P : Prop} (_ : P) => P) @Target) = ExpectedStatement := rfl` and a bridge
  theorem, audits the transitive axioms of target, equality witness and bridge, records
  sha256 of every regular file under project, dependency and toolchain roots and compares
  the record against a second pass after the run, refuses a reused log directory, ends each
  child's process group, and reports `TIMEOUT` as its own outcome, never as a mathematical
  result. `--replay` runs the toolchain's own `leanchecker --fresh` over the acceptance
  module; the strict policy admits any subset of `{propext, Classical.choice, Quot.sound}`.
- FACT (`ROLES.md:30-95`): nine bounded roles, each with an operator list and a stated
  allowed conclusion; `REVIEW-PROMPTS.md:11` records independence per axis: who authored it and in what
  context, the mathematical route taken, the encoding, the implementation, the backend, the
  exporter, the kernel.
- FACT (`RESUME-AND-ORCHESTRATION.md`, "Compact state"): negative knowledge is preserved in
  six fields: exact rejected claim, first unsupported step, witness or diagnostic, checked
  survivors, scope of the attempt, reopening condition.

## 3. The mapping

| # | Discipline | Where in the skill | Maps onto | Tag | Verdict |
|---|---|---|---|---|---|
| 1 | Proof is not a proof label | `SKILL.md:64`, `EPISTEMICS.md:17` | The tag is derived, never set: `justify` reads typed evidence nodes (PLAN §7:986-1003; `src/cairn/justify.py`) | FACT | Already Cairn's. No bullet |
| 2 | No self-certification; author, kernel, semantic, replication and external-kernel checks reported apart | `SKILL.md:65`, `EPISTEMICS.md:21` | The gate computes the axiom set itself (F5); the Skeptic sees the statement only (PLAN §7:1070-1088); the gate-run record names gate and arm (F2). `.5.9` pastes the gate's per-theorem axiom set beside the author's own `#print axioms`, marked as such | FACT for the gate; INFERRED for the bullet | Already Cairn's at the gate; **P-9d** for the library items |
| 3 | Construction beats certification | `SKILL.md:67` | Check iv is the comparator's closure comparison; the hash names and binds and decides nothing (F4 body step 3, F6 body step 3) | FACT | Already Cairn's. No bullet |
| 4 | Falsify before proving: a cheap boundary case for every new load-bearing statement | `SKILL.md:69`, `EPISTEMICS.md:29` | `.5.9`: each library item's Challenge gets a degenerate-instance probe in a `#eval`/`example` under the pinned mathlib ahead of any Solution attempt; F8's bounded prove/disprove is the mechanical form for arbitrary statements | INFERRED | **P-9a** |
| 5 | Exact statement before strategy: original prose, normalized mathematics, elaborated Lean type, each normalization explained | `SKILL.md:71`, `STATEMENT-FIDELITY.md:1-20` | F3's binding (claim statement node → Challenge) pins the outer two; the middle is the node's typed fields. `.5.9` authors three statements by hand, so the triple is pasted per item with `set_option pp.all true in #check @Target` | FACT for the binding; INFERRED for the bullet | **P-9b** |
| 6 | Status upgrades require new evidence; contrary evidence suspends, marks descendants for revalidation, never mass-falsifies | `SKILL.md:73`, `EPISTEMICS.md:37,109-122` | Tag history append-only with an evidence pointer per downgrade (PLAN §7:1043-1047); the transitive `justified_by` downgrade re-derivation walk (`cairn-m1-cqt.8.6`, closed `c2a86e7`) | FACT | Already Cairn's. No bullet |
| 7 | Orchestration has no mathematical authority | `SKILL.md:75` | AGENTS.md RULE 2; PLAN §0 | FACT | Already Cairn's. No bullet |
| 8 | Hardness is a valid research outcome | `SKILL.md:76` | PLAN §0 (progress is knowledge gained); the dead-end ledger (`cairn-m2-vgh`) | FACT | Already Cairn's; the record shape is row 10 |
| 9 | Correctness and novelty are separate; novelty defaults to not assessed | `SKILL.md:78` | PLAN §7:983-986: mechanism and novelty attribution are the Librarian's and the human's question, never a calibration class | FACT | Already Cairn's. No bullet |
| 10 | Negative knowledge in six fields | `SKILL.md:80`, `RESUME-AND-ORCHESTRATION.md` "Compact state" | `cairn-m2-vgh`'s dead-end ledger entry (refuted-by-hypothesis-key vs parked) carries the six fields; `.5.9` records an item that reaches no green gate run in the same shape | INFERRED | **P-9c**; §6 comment on `cairn-m2-vgh` |
| 11 | Proof-sounding filler is linted | `SKILL.md:82` | No surface: the Prover submits a Solution module, the Skeptic never reads proof text (PLAN §7:1070-1088), and the gate reads the kernel's verdict | FACT | Does not map. Rejected, §8 |
| 12 | Reviewer-controlled expected type proved definitionally equal to the target by `rfl`, with the bridge's own axioms audited | `TOOLS-AND-TRUST.md:88-108`, `check.py` acceptance module | The Challenge is gate-rendered from the claim statement node, so the expected type is the Challenge itself; check iv compares closures structurally. No gate-owned bridge declaration exists in the protocol: F5's module imports the Solution and collects axioms over the Challenge's theorem names, and F6's comparison produces no theorem | FACT for the skill; INFERRED for the absence of a bridge | Does not map; recorded so nobody adds a bridge theorem without an axiom audit on it |
| 13 | Input snapshot: sha256 of every regular file under project, dependency and toolchain roots, compared across the run; a persistent change fails | `TOOLS-AND-TRUST.md:119-126`, `check.py:148` | F6 on the `dev-macos-fake-landrun` arm, which runs unsandboxed (F2 record §5): a fingerprint over `lean/Challenge/`, `lean/lakefile.toml`, `lean/lake-manifest.json`, `lean/lean-toolchain` and the Solution file, taken pre-build and post-replay, mismatch fails closed and is named in the plan record. The gold arm has landrun read-only mounts, so the fingerprint is a second witness there | ABSENCE (`grep -n -i snapshot\|fingerprint src/cairn/challenge.py src/cairn/lean.py` finds none); the bullet is INFERRED | **P-6b** |
| 14 | A reused log directory is refused; outputs go to a fresh directory | `TOOLS-AND-TRUST.md:126` | Attempts are content-addressed and never overwritten (PLAN §3:154) | FACT | Already Cairn's. No bullet |
| 15 | Timeout is its own outcome, never a negative mathematical result; the child's process group is ended | `TOOLS-AND-TRUST.md:110-117`, `check.py:229` | `lean.run_argv` starts a new session, kills the process group and raises `LeanTimeout` (`src/cairn/lean.py:109-128`). The plan record's step-outcome vocabulary carries no `timeout` value that a grep of `src/cairn/gateplan.py` finds | FACT for lean.py; ABSENCE for the plan vocabulary | **P-6c** |
| 16 | An unsupported isolation backend fails `UNSUPPORTED`; never fall back to an unsandboxed command | `TOOLS-AND-TRUST.md:135-149` | `container.assert_arm` admits exactly two named arms and the gold tier refuses the dev arm (F2, `src/cairn/container.py`) | FACT | Already Cairn's. No bullet |
| 17 | `--reviewed-source` records an acknowledgment and proves nothing | `TOOLS-AND-TRUST.md:128-133` | `review_verdict` is a typed node written only through the human path (PLAN §7:1053-1064) | FACT | Already Cairn's. No bullet |
| 18 | Independence recorded per axis: who authored it and in what context, the mathematical route, the encoding, the implementation, the backend, the exporter, the kernel | `REVIEW-PROMPTS.md:11` | `.6.2`'s Skeptic checklist: a claim-agnostic closing item that names which axes the Skeptic shares with the Prover. By construction Cairn separates author/context (fresh top-level dispatch, PLAN §7:1072) and, at gold, kernel (external kernel in the container, F2); route, encoding, implementation and backend are shared by design (one mathlib, one Challenge) | INFERRED | **P-62a** |
| 19 | Statement auditor: implicit binders and universes, coercions and inferred instances, quantifier order, degeneracies, existence versus uniqueness, necessary versus sufficient, the purpose of a contradiction argument | `ROLES.md:30-35` | PLAN §7:1056-1058's checklist has quantifier order, strict versus non-strict, implication direction, domain and boundary. The four items PLAN's list lacks: binders and universes, coercions and instances, existence versus uniqueness, the purpose of a contradiction argument | FACT for both lists; the gap is INFERRED | **P-62b** |
| 20 | Trust auditor: an empty or absent target set is rejected | `ROLES.md:65-70`, `check.py` `load_spec` ("empty expected target/module set") | F5's module collects axioms over the Challenge's theorem names; the body states no clause for zero names, under which `⊆` holds vacuously | ABSENCE in the F5 body | **P-5a** |
| 21 | Unused admissions outside the accepted closure do not contaminate it; challenge placeholders may exist only outside the closure | `TOOLS-AND-TRUST.md:57-58`, `ROLES.md:65-70` | F5 collects over the Challenge theorem names, so under the body as written a `sorry` in a Solution declaration outside that closure passes the axiom step. The behavior is undecided in any bead | ABSENCE | **P-5b**: pin the behavior with a fixture and name the admission in the record |
| 22 | A forged environment: a module that adds an unchecked declaration through the elaborator, caught only by kernel replay; the negative fixture is valid only beside a positive replay in the same run | `NOTICE.md:26-31`, `SELF-TEST.md` "Selecting replay-forged also requires replay-positive" | F6's self-tests plant a `sorry` (stops at the axiom step) and a weaker statement (stops at closure comparison); nothing plants a failure at the kernel-replay step. `.3.3`'s family (c) and (d) likewise | ABSENCE in F6 and .3.3 bodies; the artifact is FACT (§1) | **P-6d**, **P-33a** |
| 23 | Fifty named failure modes; a coverage row per class in a fixture matrix | `FAILURE-MODES.md:61-83,167-181` (FM11 quantifier drift, FM12 quantifier-order confusion, FM13 domain drift, FM14 statement weakening, FM15 hidden non-vacuity failure, FM36 formalization mismatch, FM37 hidden axioms or placeholders, FM38 formalization-by-tautology) | F8's fixture table and `.6.2`'s checklist: one matrix assigning each class to a pre-filter, to a checklist item, or to an explicit uncovered row, so no class is owned by nobody. Cairn's own names are used for the classes; the skill's numbers are the cross-reference | INFERRED | **P-8a** |
| 24 | "Kernel accepted; semantic review pending" is a precise state | `SKILL.md:130-134` | A green `lean_artifact` without an `approve` verdict stays at its pre-review tag on the human queue (PLAN §7:1064-1067; `cairn-m1-cqt.7.2`) | FACT | Already Cairn's. No bullet |
| 25 | A proof of `H → T` with a new premise `H` is complete as an implication while `T` stays open; the prover may propose a changed theorem but never adopt it silently | `SKILL.md:136-141`, `EPISTEMICS.md:33` | A Solution proving `H → T` is a different statement and fails check iv; the changed statement is a new claim statement node. The Formalizer's typed submission has no field for proposing that change | FACT for the gate; ABSENCE for the submission field | §6 comment on `cairn-m2-vgh` |
| 26 | A compact factual record beside the source for short work; ledgers only for a campaign | `RESUME-AND-ORCHESTRATION.md` "Compact state", `SKILL.md:150-155` | The gate-run record, the binding and the ARTIFACTS block carry the fields; `.5.9`'s triple (P-9b) lands in the grounding row, not in a notes file | FACT | Partial: covered by P-9b; no notes file |
| 27 | Library scout: a plausible theorem name is only a query; read the exact signature at the pin | `ROLES.md:37-42` | `.5.9` [R4] says re-verify against the pinned revision; the bullet makes the absence claim ("not in mathlib at `1f29011`") a pasted failing `#check` and every used declaration a file:line cite at that revision | INFERRED | **P-9e** |
| 28 | Bounded workers coordinated through Agent Mail reservations and build slots | `RESUME-AND-ORCHESTRATION.md` "Bounded workers" | AGENTS.md: single-agent repository; `agent-mail` installed and unused | FACT | Rejected, §8 |
| 29 | Selective `cass` history mining | `RESUME-AND-ORCHESTRATION.md` "Selective history mining" | Excluded by the operator for this lane (`skills-fit-formalization-lane.md` §6) | FACT | Rejected, §8 |
| 30 | Proof beads with production → review → accepted-integration edges; an attempt bead may close while the theorem stays open, said in the reason | `RESUME-AND-ORCHESTRATION.md` "Optional proof beads" | Research is not pre-decomposed into beads (AGENTS.md); the edge typing matches `.3.3 → .7.2`. The close-with-disposition rule is P-9c's second clause | FACT | No bullet beyond P-9c |
| 31 | Native evaluation trust: inspect the actual native-generated assumptions rather than assume `Lean.ofReduceBool` | `TOOLS-AND-TRUST.md:63-65` | F5-b already records observed names from `collectAxioms` on `v4.34.0-rc1` | FACT | Already Cairn's (cairn-9zp). No bullet |
| 32 | `diagnose.py` reads pins and resources without running project code | `scripts/diagnose.py:1-30` | `cairn env --json`; `lean.assert_pinned` (`src/cairn/lean.py:167`) | FACT | Already Cairn's. No bullet |
| 33 | `bootstrap.py` downloads a pinned toolchain with checked SHA256 | `TOOLS-AND-TRUST.md:27-37` | F1 (elan, closed) and the container's `ELAN_SHA256`/`LEAN_SHA256` build args (`src/cairn/container.py:106-116`) | FACT | Already Cairn's. No bullet |
| 34 | Two clean independent review passes for a substantive development; none manufactured | `SKILL.md:146-148` | The human `review_verdict` and the Skeptic; the count is the human's call at H2 | FACT | No bullet |
| 35 | Modes `construct`, `audit-only`, `repair`, `simplify`, `expand`, `resume`; audit permits inspection, not edits | `SKILL.md:38-40` | `research/SESSION-PROMPTS.md` Mode A on a `lean/` bead: the row in §7 names the mode per bead | INFERRED | §7 row |
| 36 | Code-oriented fresh-eyes prompts for scripts, metaprograms and harnesses; mutate a hypothesis, target list, universe or exit path and verify rejection while positives still pass | `ROLES.md:97-111` | The lane's mutation-proof discipline at close (F2 close, six proofs) and `.githooks/pre-commit`'s Opus review | FACT | Already Cairn's. No bullet |

## 4. Adopted bullets, as `br update` text

Each bullet is a pasted observable at the named bead's close. Prefix `P-` distinguishes them
from the `F4-`/`F5-` bullets cairn-9zp added.

### `cairn-m1-cqt.5.5` (F5) gains

- **P-5a Empty target set fails closed** (row 20): a Challenge whose theorem-name list is
  empty is refused by the axiom step with a named reason, never passed on a vacuous `⊆`;
  the fixture and its refusal line pasted.
- **P-5b Unused admission pinned** (row 21): a Solution carrying `sorry` in a declaration
  outside the Challenge theorems' transitive closure has its behavior at the axiom step
  decided and pinned by a fixture: the step passes on the closure, and the record names
  the unused admission as a flag (never silently). The decision and its reason land in the
  grounding row beside the F5-a matrix; the fixture output and the record line pasted.

### `cairn-m1-cqt.5.6` (F6) gains

- **P-6b Input fingerprint on the dev arm** (row 13): on `dev-macos-fake-landrun` the gate
  takes a sha256 fingerprint over `lean/Challenge/`, `lean/lakefile.toml`,
  `lean/lake-manifest.json`, `lean/lean-toolchain` and the Solution file ahead of the
  sandbox build and again after kernel replay; a mismatch fails closed at the step where it
  is observed and the plan record names the changed path. Planted: a Solution whose build
  step rewrites a Challenge file is refused with that path named; pasted. On the gold arm
  the same fingerprint runs and its equality is pasted as the second witness beside
  landrun's read-only mounts.
- **P-6c Timeout is its own step outcome** (row 15): the plan record's step-outcome
  vocabulary distinguishes `timeout` from `fail`; a planted slow Solution run under a
  reduced `lean.DEFAULT_TIMEOUT_S` stops at `timeout` with later steps blocked, and the
  record line pasted shows `timeout`, never `fail`.
- **P-6d Kernel-replay failure planted** (row 22): a Solution module adapted from lean4's
  `tests/pkg/leanchecker/LeanCheckerTests/AddFalse.lean` at commit `3447a668` (Apache-2.0,
  attribution in the fixture file), which adds an unchecked `false : False` through
  `Environment.addDeclCore` with `doCheck := false`, passes the axiom step and fails at
  `leanchecker --fresh`; it runs in the same test as the exact-match positive, so the
  negative is attributed to the forgery and not to the environment; both verdict lines and
  the step at which each stopped pasted. A second fixture from the same family
  (`ReplaceAxiom.lean` or `AddFalseConstructor.lean`) is added if its failure lands at a
  different step; otherwise the grounding row says why one suffices. Precondition the bullet
  rests on, undecided in any bead and absent from `src/cairn/` (no Solution build path
  exists; `challenge.py` renders the Challenge only): the Solution module is compiled so
  its elaborator commands run, and `import Lean` is admissible in a Solution. F6 states
  the answer in its grounding row ahead of the fixture; if a Solution may not `import
  Lean`, the planting moves to the level the protocol admits or the row says none does.

### `cairn-m1-cqt.5.8` (F8) gains

- **P-8a Coverage matrix across pre-filters and the Skeptic's checklist** (row 23): one
  table with a row per statement-level failure class the lane names (vacuous hypotheses;
  the `∃ x, P x → Q` trap in plain, binder-predicate and conjunction-nested forms; stub;
  new axiom; trivially provable; trivially disprovable; round-trip divergence; quantifier
  drift; quantifier-order confusion; domain drift; statement weakening; hidden placeholder;
  tautology), each assigned to the pre-filter that fires, the Skeptic checklist item that
  carries it (`.6.2`), or an explicit uncovered row with its reason. The two nested ∃-trap
  forms appear as checklist-carried, matching the pinned linter limitation. The table is
  pasted at close and lands in `research/grounding/lean-statement-linters-vacuity.md`.

### `cairn-m1-cqt.5.9` (library items) gains

- **P-9a Falsifier ahead of the Solution** (row 4): each item's Challenge statement gets a
  degenerate-instance probe under the pinned mathlib ahead of any Solution attempt, as an
  `example` or `#eval` in a scratch module: the DLP definition on the trivial subgroup and
  with `P = 0`, the finiteness statement over the smallest field the definition admits, the
  Hasse bound at `q = 2` and `q = 3`; a probe that refutes the statement sends the item back
  to statement authoring, never to the Solution. Probe files and their output pasted.
- **P-9b The three-statement triple** (row 5): for each item, the close pastes the source
  locator (PLAN §11 line), the normalized statement with every normalization named, and the
  elaborated type from `set_option pp.all true in #check @<Target>` at the pinned toolchain;
  a normalization with no stated reason is a defect. The triple lands in the grounding row
  for the item.
- **P-9c No partial item, and the six-field record for one that stalls** (row 10): an item
  that reaches no green gate run leaves the bead open and records, in the grounding row:
  the exact statement attempted, the first unsupported step, the witness or diagnostic, the
  checked survivors (lemmas that compiled), the scope of the attempt (toolchain, mathlib
  revision, wall time, route), and the reopening condition. The record pasted where it
  applies; otherwise the close says no item stalled.
- **P-9d Axioms per item, transitively** (row 2): each Solution's transitive axiom
  set is the gate's F5 output, pasted per theorem name, beside a `#print axioms` run by the
  author as a separate line marked author-check; the two agree or the disagreement is the
  finding.
- **P-9e Library facts at the pin** (row 27): every mathlib declaration a Solution uses is
  cited at file:line at mathlib `1f29011`, and the claim that an item is absent upstream is
  shown by a failing `#check` or an empty `grep` over the pinned checkout, pasted; a
  declaration found upstream turns that item into an import with its own statement match,
  recorded in PLAN §11's coverage line.

### `cairn-m1-cqt.3.3` (Lean fixtures) gains

- **P-33a Family (c) gains the forged-environment planting** (row 22): the
  `AddFalse`-derived Solution from F6's P-6d is registered as a cold planting whose expected
  catch step is kernel replay, distinct from the `sorryAx` planting's axiom step; the
  registry row and the plan-record assertion that it reached `--fresh` and failed there are
  pasted, beside the exact-match positive from the same run.

### `cairn-m1-cqt.6.2` (role templates) gains

- **P-62a Independence axes as a checklist item** (row 18): the Skeptic's checklist ends
  with a claim-agnostic item that names the axes (author and context, mathematical route,
  encoding, implementation, backend, kernel) and asks which are shared with the Prover on
  this dispatch; the template text pasted, and `tests/unit/test_role_templates.py` asserts
  the item is present by keyword.
- **P-62b Four statement-audit items** (row 19): the checklist carries, in Cairn's words,
  implicit binders and universes; coercions and inferred instances; existence versus
  uniqueness; and the purpose of a contradiction argument (a request to construct an object
  answered by an empty domain is a fidelity defect). Each item is present by keyword in the
  unit test, and the claim-agnostic check still passes; pasted.

### `cairn-m1-cqt.5.4` (F4) gains no bullet

Rows 3 and 12 land on F4's existing body: the hash names and binds and decides nothing,
and check iv is the comparator's closure comparison. Row 5's binding is F3's, closed. The
skill adds no mechanic F4's steps lack, so F4 carries only the dependency edge on this bead.

## 5. Where the skill's proof craft belongs

The unread references (`PROOF-PATTERNS.md`, `CREATIVE-PROOF-DEVELOPMENT.md`, the four
FERMAT files, `OPERATORS.md`, `LOCALIZATION.md`) are tactic selection, library search and
route change for the agent writing a Solution. In M1 the only bead that writes a Solution is
`.5.9`; F4, F5, F6 and F8 write Python and Lean metaprogramming, where `SKILL.md:36-60`
(smallest useful task, pinned `lake env lean`, isolation) and the code-review prompts
(`ROLES.md:97-111`) apply and the proof craft does not. From M2 the Formalizer worker
writes Solutions inside Cairn; §6 states how the skill reaches it without its text entering
the tree.

## 6. Design comment for `cairn-m2-vgh` (Formalizer worker, dead-end ledger)

Recorded as a bead comment; decomposition waits for M1 close per the bead body.

- The dead-end ledger entry carries the six negative-knowledge fields (row 10): exact
  rejected claim (the claim statement hash), first unsupported step, witness or diagnostic
  (a hash of the artifact), checked survivors (lemma names with their own axiom sets),
  scope of the attempt (toolchain, mathlib revision, wall time, route), reopening
  condition. `refuted` versus `parked` is a disposition over that record, not a replacement
  for it. INFERRED.
- The Formalizer's typed submission gains `proposed_statement_change`: a new informal
  statement plus the reason, routed to the human queue as a `statement_review` item, never
  applied by the worker (row 25). A Solution proving `H → T` for a new `H` is submitted
  against a new claim statement node carrying `H`, and the record links the two. INFERRED.
- The Prover's role template for the Formalizer names the skill by name, version and
  skill_hash as the discipline the worker runs under; the harness loads the skill from the
  operator's machine at dispatch and the dispatch record (W1) pins the loaded file's
  sha256 beside the template hash. The skill's text stays outside the tree and the bundle;
  the ledger fact is which version ran. The trade: a file outside the bundle is not pinned
  by the bundle hash, so the dispatch record is its pin. INFERRED; operator decision at M2.
- The Skeptic checklist items of P-62a and P-62b are M1 (`.6.2`); the Formalizer inherits
  them unchanged.

## 7. Session opener row

`research/SESSION-PROMPTS.md`'s skill table gains one row: the skill loads in Mode A when
the bead touches `lean/` or writes Lean metaprogramming, in `construct` for a Solution
(`.5.9`, and the Formalizer from M2), in `audit-only` when reviewing a fixture family
(`.3.3`) or another session's Lean, and with the code-review prompts for gate code (F4, F5,
F6, F8). The row states the license boundary in one clause so a session never pastes the
skill's text into a bead or a template.

## 8. Rejected, with the reason

- Vendoring `SKILL.md`, `ROLES.md` or `REVIEW-PROMPTS.md` as gate-bundle role templates:
  proprietary text in a public MIT tree, and a bundle hash bound to a third-party file.
  The templates are written in Cairn's words (P-62a, P-62b) and the skill is cited.
- Vendoring `scripts/check.py` or running it as Cairn's gate: it is pinned to Lean 4.33.1
  and its spec schema; Cairn's gate is the Challenge/Solution protocol on `v4.34.0-rc1`
  with the comparator's closure comparison as the decision. Its mechanics that Cairn lacks
  are adopted as P-5a, P-6b, P-6c, P-6d.
- The `rfl` bridge theorem (row 12): the protocol has no expected-type file separate from
  the Challenge, so there is nothing for a bridge to compare; adding one would add a
  declaration whose axioms need auditing for no gain.
- Law 11's prose linter (row 11): no prose proof surface exists in the gate.
- Agent Mail reservations, build slots and `cass` mining (rows 28, 29): single-agent
  repository; operator exclusion.
- A `PROOF_NOTES.md` beside each library item (row 26): the grounding row carries the
  triple and the record; a second file is ceremony.
- `CLAIMS_LEDGER.md` and `EXPERIMENT_DESIGNS.md`: the substrate's typed nodes and lineage
  edges are that ledger, under a hash.
- The skill's `bootstrap.py` and 4.33.1 example environment: F1 is closed on `v4.34.0-rc1`
  and the container carries checked SHA256 build args.

## 9. No-Claim

This brief proves what the skill says and where each discipline lands in Cairn. It does not
prove that a discipline helps: that is shown, or not, when a close on an amended bead pastes
the observable its bullet names. A bullet whose close carries no pasted output is a bullet
this brief got wrong, and the close should say so rather than paste around it. Nothing here
changes a gate, the calibration taxonomy, the ladder, the verifier or what counts as
proven; every bullet adds a check or a record and removes none.
