# MAP.md — Cairn as one system

Read `CLAUDE.md` first (the invariants), this file second (the shape), `PLAN.md` third (the
strategy, by its section map in `CLAUDE.md`), and `research/` when a claim needs its evidence.
This file is the tower: one row per layer naming what has authority over the layer's
correctness and the language that authority is written in, the identity primitive that
content-addresses it, the record kinds it writes, the `cairn` verbs that drive it, and what it
refuses. Bead `cairn-sm1` holds the test that pins this map to the code: every registered
command, every claims kind, every gate name and every gate-bundle object kind must appear here
verbatim, so the map and the registry cannot disagree without a red test.

## Two rules order the tower

1. **Mutable strategy, immutable epistemics** (PLAN §0). Layers 6 and up may rewrite
   anything in layers 8 and 9; nothing may rewrite layers 4 through 7.
2. **The authority-language rule** (PLAN §16 decision 13). A layer is implemented in the
   language of the thing that has authority over its correctness: the Lean kernel for
   statement identity, axioms and replay; libpari or a compiled skill for arithmetic; Python
   3.14 for everything with no other authority. A component that parses another authority's
   printed output to reconstruct its verdict is a gate that is a label.

## The layers, bottom up

| # | Layer (code) | Authority and its language | Identity primitive | Record kinds | `cairn` verbs | Refuses on |
|---|---|---|---|---|---|---|
| 1 | Bytes and hashes (`canon.py`, `keys.py`, `kat.py`) | the canonical encoding and BLAKE3 domain tags, Python | domain-tagged digest | `tests/vectors/canon_kat.json`, `claims_kat.json` | `kat` | KAT drift |
| 2 | Skills (`src/cairn/skills/`, `pari.py`, `ec.py`, `witness.py`, `selftest.py`, `selftest_skills.py`, `measure.py`, `profile.py`) | the skill's backend: libpari through cypari2 and `gp` (C); a compiled binary when PLAN §16 decision 2 funds one | identity bundle hash {interface version, implementation revision, tool digests, container digest, numeric profile}; recipe key | selftest certificate, receipt, corpus ledger with `pass_floor`, cost profile | `selftest`, `measure` | floor miss, certificate mismatch, double-run divergence, `DISAGREE`, yank |
| 3 | Substrate (`substrate.py`, `schema.sql`, `attest.py`, `gc.py`, `env.py`, `instances.py`) | SQLite under the write boundary (`chflags` on macOS, `chattr` in the container), Python | node hash; hypothesis key; instance hash; env manifest hash | `hypothesis_object`, `claim_statement`, `evidence_node` (kinds `lean_artifact`, `ladder_table`, `repro_node`, `counterexample_hunt_record`, `statistical`, `model_proof`), `repro_record` (kinds `second_attempt_agree`, `witness_check`), `review_verdict`, `gate_run`, `ticket` | `attest`, `gc`, `env` | write-boundary violation, unreachable root, unpinned attestation |
| 4 | Gates (`bundle.py`, `gateplan.py`, `ladderplan.py`, `verifier.py`, `tiergate.py`, `runner.py`) | the gate bundle: objects `allow_lists`, `auditor`, `gate_plan`, `ladder_plan`, `lean`, `role_templates`, `tiers`, `verifier`, `waivable_checks`, `verifier_script` (`src/cairn/gp/verify.gp`), `lake_manifest` (`lean/lake-manifest.json`), `challenge_prelude` (`bundle/challenge_prelude.lean`), `challenge_renderer` (`src/cairn/challenge.py`); the verifier is `gp`, Python invokes | bundle hash under the operator pin; ticket hash | `gate_run` with gate names `canon_kat`, `verifier`, `tier_gate`, `self_test`, `gate_plan`, `bundle_open`, `ladder_plan`, `challenge_render` | `bundle`, `gate`, `ladder` | bundle hash ≠ pin, plan-step verdict ≠ expected, `xP ≠ Q`, tier two above, uncertified or yanked revision, budget ceiling |
| 5 | Formalization gate (`lean.py`, `challenge.py`; PLAN M1 F1–F8, beads `cairn-m1-cqt.5.*`) | the Lean kernel: the comparator, `leanchecker --fresh`, the statement hasher as a `lake exe`, on `leanprover/lean4:v4.34.0-rc1` with mathlib at the pinned revision, under `landrun` in the Linux container for the gold tier; Python renders the Challenge from the claim statement under the pinned prelude into `lean/Challenge/` (gate-owned), invokes, and records | toolchain name plus lean commit; mathlib revision; renderer and prelude hashes; formal statement hash bound to the claim statement hash in the `challenge_render` gate-run record; input-addressed container digest (PLAN §16 decision 14) | `gate_run` carrying the binding and the arm that ran; `lean_artifact` evidence; a `Submission` is a Solution module plus the formal statement hash it names, nothing else | the F-bead verbs | toolchain commit ≠ pin, a Challenge outside the gate-owned directory, a binding absent from the record, statement mismatch, axioms outside {`propext`, `Classical.choice`, `Quot.sound`}, replay failure, arm unnamed |
| 6 | Epistemics (`justify.py`, `claims.py`) | the calibration taxonomy, immutable | the tag on a claim: `SPECULATION`, `CONJECTURE`, `STRONG-EMPIRICAL`, `PROVEN` | statement statuses `open`, `refuted`, `promoted`, `withdrawn`; ledger entries; the negative-results map (beads `cairn-m1-cqt.8.*`) | `justify` | a tag above its evidence, a small-case pattern promoted without the counterexample hunt |
| 7 | Ladder, tiers, escrow, yank (`tiergate.py`, `measure.py`; beads `cairn-m1-cqt.1.*`, `.4.*`) | measured cost profiles and the ladder's result tables | ticket hash; yank record with its reach predicate | ticket, yank, ladder table, A/A null arm | `gate`, `measure` | `TierRefused`, cost drift, `SKILL_YANKED` |
| 8 | Workers (beads `cairn-m1-cqt.6.*`) | role templates pinned in the bundle; the Claude Agent SDK | template hash; attempt id | attempt records, worker outputs as untrusted proposals | dispatch (M1) | budget exceeded, a worker writing a gate-owned path, an unpinned template |
| 9 | Orchestrator (PLAN §15 P3; M3) | the tick table in SQLite, Python | tick hash with the source hash of every step | tick records with stored RNG draws | (M3) | replaying a step whose body changed |
| 10 | Human path (beads `cairn-m1-cqt.7.*`) | review verdicts and waivers by an attributed human | review verdict hash | `review_verdict` (`approve`, `reject`, `needs_revision`), waiver, queue item | queue (M1) | an unratified claim statement, a waiver on a non-waivable check, throughput ceiling |
| 11 | Builder harness (`scripts/`, `.githooks/`, `.beads/`, `tests/`, `research/grounding/`) | `scripts/check.sh` is the definition of green; the compliance audit; the goldens | commit SHA; bead id; golden file | close comments with ARTIFACTS blocks, `.check.log`, scorecards, grounding briefs | `capabilities`, `doctor`, `robot-docs`, `startup-scan`, `m0-run` | a red gate, a close without an artifact block or a test plan, an unverifiable audit |

## One identity per thing

Bytes have a domain-tagged BLAKE3 digest. A skill has an identity bundle hash. A run has a
recipe key. An environment has an input-addressed container digest. A gate configuration has
a bundle hash and an operator pin. A claim has a claim statement hash; its formalization has a
formal statement hash bound to it in a gate run. A decision has a gate-run hash. A toolchain
has a name and a commit. Nothing is identified by a label, a path or a build timestamp.

## One control surface

The `cairn` CLI is the control surface for agents and humans alike: every command registers
with `--json`/`--robot`, dry-run by default where an act is irreversible and `--force` to
perform it, the exit-code vocabulary in `exits.py`, and `capabilities --json` as the contract
an agent reads once per session. MCP is not a control surface for driving `cairn`. One
read-only status call rendering the whole state and the admissible commands is a child of
bead `cairn-sm1`.

## Feedback tiers

`scripts/check.sh --fast` answers in seconds (format, lint, spelling, types, theater). A unit
tier under one minute is a child of bead `cairn-sm1`. The full suite is the definition of
green for a bead close and for CI, which bills macOS at ten times wall clock.

## Where the evidence lives

`research/grounding/` holds facts established by executing them on this machine, tagged;
`research/briefs/` holds per-source reading; `research/PROPOSALS.md` holds the rationale for
every mechanism in `PLAN.md`; `research/briefs/language-and-agent-ergonomics.md` holds the
evidence for the authority-language rule and the coordination-language default.
