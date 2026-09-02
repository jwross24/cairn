# Brief: the coordination language, the authority-language rule, and agent ergonomics

Review date 2026-09-02. Question put by the operator: was Python chosen by muscle memory, and
what stack and shape would let an LLM agent understand and drive Cairn most accurately at the
least cost. Five research gatherers (Sonnet, web search with page fetches) covered languages for
compute skills, Lean 4 as a gate language, durable orchestration, agent-ergonomic design, and
hermetic environments. Their reports are claims, not evidence: each row below carries the tag
the gatherer assigned and the URL it read, and a row that changes a design lands only through
the bead that acts on it, which re-verifies it on this machine.

Tags: **FACT** = the gatherer fetched and read the cited page; **REPORTED** = taken from a
search summary, not independently fetched; **INFERRED** = reasoning, no page says it;
**ABSENCE** = nothing found, which is not evidence of nothing.

## 0. The answer in one paragraph

Python is not the source of Cairn's determinism and was never recorded as a decision. The
determinism comes from content-addressing and canonical encoding (§3), the skill contract is a
process boundary with canonical JSON on stdin and stdout (§2), and the kernel-facing checks are
Lean programs whatever language invokes them. Under that shape the coordination language is a
property of the *authors*: LLM agents write Python with the lowest defect rate of any language
in the surveyed evidence, the test discipline that keeps the builder honest (2006 tests,
Hypothesis, goldens, mutation checks) is Python-native, and every surveyed alternative for the
harness itself (Rust, Lean 4 as a systems language, Elixir/OTP) costs the whole suite for a
benefit no source measured. So: Python 3.14 via uv stays as the coordination language, recorded
in PLAN §16 as an operator default with its revisit triggers; the **authority-language rule**
(PLAN §16 decision 13) states where Python must not be the implementation; the container
identity is input-addressed (decision 14); and the accretive changes are legibility and
feedback-loop changes, not a rewrite (`MAP.md`, `cairn status`, a unit tier of the suite).

## 1. Languages for deterministic compute skills

- Rust binaries are reproducible when the toolchain and build paths are pinned; Cargo strips
  nondeterministic metadata and `repro-check` verifies compiler reproducibility; the February
  2025 report lists open reproducibility bugs targeted at 1.83/1.84.
  FACT — https://reproducible-builds.org/reports/2025-02/ · https://reproducible-builds.org/docs/rust/
- No page states that cypari2 or PARI/GP guarantees bit-identical output across machines;
  PARI real-number precision is word-size dependent. FACT —
  https://cypari2.readthedocs.io/en/latest/pari_instance.html. Cairn's skills stay in exact
  integer and finite-field arithmetic, which sidesteps it: INFERRED by the gatherer, and the
  §2 numeric-profile field exists for the day a skill does not.
- LLM code quality by language: on C-to-safe-Rust transpilation (CRUST-Bench) Claude Opus 4
  single-shot 22 %, o3 19 %, 40–48 % with a three-round repair loop; most open-weight models
  0–2 %. FACT — https://arxiv.org/html/2504.15254v3. Transpilation overstates greenfield
  difficulty: INFERRED. A multi-language error-taxonomy study reports C++ NameError rates far
  above Python's and non-significant Python–Rust and Python–Java gaps. REPORTED — arXiv
  2605.30394 via search summary.
- Per-model Rust compilation-error rates of 18 % (o1-mini), 39 % (DeepSeek R1), 27 % (Claude 3.5
  Sonnet), and one study finding 94 % of LLM compilation errors are type-check failures.
  REPORTED — https://yuv.ai/blog/ai-pushing-typed-languages. The actionable reading for a
  Python harness is that type checking is where LLM-authored defects surface, so `ty check`
  in `scripts/check.sh` is the compiler-equivalent channel and its strictness is the lever.
- Tooling state: PARI/GP stable 2.17.4 (2026-06-29), alpha 2.18.1 (2026-07-24). FACT —
  https://pari.math.u-bordeaux.fr/. FLINT stable 3.2.1 (2025-03-15), Arb/Antic/Calcium merged,
  ECM module present; no full elliptic-curve-group API comparable to PARI's `ell*` surfaced.
  REPORTED — https://flintlib.org/download/flint-3.2.1.pdf. Nemo/Hecke/Oscar are maintained
  (Oscar docs 2025-06) with finite-field and elliptic-curve APIs at the Hecke layer over
  FLINT/Antic. REPORTED — https://docs.oscar-system.org/v1/Hecke/manual/elliptic_curves/finite_fields/
- CADO-NFS's README section read documents integer factorization only; its finite-field DLP
  mode is INFERRED from the literature and unverified here. FACT for the README —
  https://github.com/cado-nfs/cado-nfs/blob/master/README.md
- No 2025–2026 ECDLP record computation surfaced; only the 113-bit Koblitz FPGA result and
  small CUDA rho projects (ECCp-79 in about three hours on one RTX 2070 Super). ABSENCE for the
  record; REPORTED for https://github.com/atlomak/CUDA-rho-pollard. The honest baseline of
  `HANDOFF.md` is unchanged by an absence; an eprint.iacr.org sweep is the check, not done here.
- The JSON-process contract decouples skill identity from language: a compiled skill's
  implementation revision is its source plus lockfile hash and its tool digest is the static
  binary's digest, symmetric with the Python skills. INFERRED, consistent with everything read.

## 2. Lean 4 as a gate language

- Lake 4.30.0 (2026-05-26) and a FRO roadmap naming a stable `Std` with containers, networking,
  async and an HTTP server library for mid-2026. FACT —
  https://lean-lang.org/doc/reference/latest/releases/v4.30.0/ · https://lean-lang.org/fro/roadmap/y3/
- `leanprover/leansqlite` exists with a `lake test` suite; no maturity claim beyond existence.
  FACT — https://github.com/leanprover/leansqlite
- No benchmark measures LLM fluency at Lean 4 *programs* as opposed to proofs. ABSENCE.
- The comparator checks that every declaration used in the statement of each relevant
  theorem is the same in Challenge and Solution (transitive closure, environment-level
  equality, shared prelude), enforces `permitted_axioms` from a JSON config after export and
  before kernel replay, and names landrun's correctness as part of its own trusted base. FACT —
  https://github.com/leanprover/comparator
- No tool computes a canonical hash of a Lean statement modulo proof; Formal Conjectures pins
  statements by file name plus commit hash; SafeVerify replays one olean against another's
  signatures. FACT — https://github.com/google-deepmind/formal-conjectures/blob/main/README.md ·
  https://github.com/GasStationManager/SafeVerify. The F4 hasher therefore hashes what the
  comparator compares (the grounding brief's proxy), which is the state of the art, not a gap.
- The reference manual's protocol: elaboration, `#print axioms`, `lean4checker --fresh` replay
  into a fresh environment, then comparator plus independent external kernels (nanoda, Rust)
  outside the sandbox; `@[implemented_by]` and `extern` are part of the trusted base. FACT —
  https://lean-lang.org/doc/reference/latest/ValidatingProofs/. `leanchecker` ships in the
  toolchain from 4.28.0 (2026-02-17). REPORTED — release notes via search summary.
- Axiom collection is toolchain-dependent: from Lean 4.23.0 `collectAxioms` follows axioms
  referenced by other axioms, so `#print axioms` on a `native_decide` proof lists
  `Lean.trustCompiler`; older toolchains omit it, and `@[csimp]` smuggling is tracked as
  issue 7463. FACT for the issue — https://github.com/leanprover/lean4/issues/7463; REPORTED
  for the version boundary. F5 computes the axiom set Lean-side on the pinned toolchain
  (4.34.0-rc1, above the boundary) and plants `Lean.trustCompiler` as a refused fixture.
- nanoda is a from-scratch Rust kernel usable as a comparator `external_kernels` entry. FACT —
  https://github.com/ammkrn/nanoda_lib

## 3. Durable orchestration

- DBOS defaults to SQLite for its system database, Postgres only for multi-server scale, with
  SQL-queryable workflow and step history and no documented content-addressed export. FACT —
  https://docs.dbos.dev/python/tutorials/database-connection · https://github.com/dbos-inc/dbos-transact-py
- Restate is a single self-contained binary running as a companion process, with
  `restate invocations list/describe`, `restate sql` and an HTTP query surface over
  `sys_invocation` and `sys_journal`, plus cancellation. FACT — https://restate.dev ·
  https://docs.restate.dev/operate/introspection. That surface is the bar for what
  `cairn status --json` has to show; the binary is not worth adding for it.
- A hand-rolled execution log over SQLite that replays completed steps from the log is the
  pattern PLAN §15 P3(iii) names, minus retries, parallelism and a UI. FACT —
  https://morling.dev/blog/building-durable-execution-engine-with-sqlite
- Temporal runs on SQLite as a single binary for local use; production single-node durability
  leans on Litestream; the server, UI and worker stack is heavier than the two above. REPORTED.
- Sakana AI Scientist v2 uses a progressive agentic tree search run by an experiment-manager
  agent, the nearest published precedent for a mutable tree of research branches with budgets;
  a paper and codebase, not a substrate. REPORTED — https://arxiv.org/abs/2504.08066
- LangGraph's SQLite checkpointer carried two 2026 CVEs (SQL injection, unsafe msgpack
  deserialization). REPORTED — Check Point Research. PLAN §12 excludes LangGraph and Temporal
  as the state layer; this is a second reason.
- Jido 2.0 on the BEAM (about 2026-03) with supervision trees as the agent model. REPORTED —
  https://elixirforum.com/t/jido-a-sdk-for-building-autonomous-agent-systems/68418. OTP is a
  model to study for branch-tree semantics, not a runtime to adopt: INFERRED, since it forks
  the project off Python, the Claude Agent SDK and the substrate tooling.

## 4. Agent-ergonomic design

- Anthropic: invest in the agent-computer interface as much as the human one; tool docs carry
  example usage, edge cases, input formats and boundaries; absolute over relative paths made
  a SWE-bench tool work flawlessly; minimal non-overlapping tool surfaces; context is a finite
  resource and the goal is the smallest set of high-signal tokens; tool responses capped at
  25 000 tokens by default with pagination and a `concise|detailed` knob; errors give specific
  next actions. FACT — https://www.anthropic.com/news/building-effective-agents ·
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ·
  https://www.anthropic.com/engineering/writing-tools-for-agents
- One third-party benchmark (characters/4 token estimate): raw CLI 0 fixed schema tokens per
  session, CLI plus skill about 480 once, native MCP about 3 062 injected on every prompt; a
  20-prompt session with two GitHub operations cost 61 654 tokens under MCP against 448 under
  the CLI. FACT for the page, single benchmark, approximate tokenizer —
  https://blog.mornati.net/the-future-of-agentic-tooling-mcp-servers-vs-cli-a-data-driven-comparison
- pytest-testmon selects tests by a code-to-test dependency database; no speedup figure is
  published on its page. FACT — https://github.com/tarpas/pytest-testmon. Property tests and
  goldens may defeat file-level tracking: INFERRED.
- Dependency-graph documentation and structural repository renderings measurably help agents
  navigate large repositories (LEDGE, CodexGraph, SeeRepo, Code Graph Models). REPORTED —
  https://openreview.net/forum?id=b98ODdeYq5 and others; none read in full.
- The `cairn` CLI's `--json`, dry-run default, `--force` gating, exit-code vocabulary and
  `capabilities` contract match the documented consensus. INFERRED from the pages above against
  `src/cairn/cli.py`; validated design, not a gap.

## 5. Hermetic environments and the container digest

- A Nix flake closure is content-addressed per input and its hash changes iff any input
  including the toolchain changes; `nix2container` turns the closure into an OCI image without
  losing that property. FACT — https://github.com/nlewo/nix2container and flake documentation.
- `lean4-nix` packages Lean 4 toolchains (from v4.11.0) via `lake2nix` reading
  `lake-manifest.json`, with a Garnix binary cache; mathlib's `lake exe cache get` olean step is
  not documented as integrated. FACT for the README — https://github.com/lenianiva/lean4-nix
- Determinate Nix supports Apple Silicon macOS only, from v3.13.2 (2025-11). FACT —
  https://determinate.systems/blog/nix-darwin-updates
- BuildKit's `SOURCE_DATE_EPOCH` support pins timestamps and, with `rewrite-timestamp=true`,
  file times; its documentation does not claim a stable content digest across independent
  builds. FACT — https://github.com/moby/buildkit/blob/master/docs/build-repro.md. apko is
  reproducible by construction because it forbids arbitrary execution, which makes it unfit for
  a stack that compiles PARI/GP and cypari2 without first packaging them as APKs. FACT —
  https://github.com/chainguard-dev/apko
- landrun confines filesystem access per path and, on kernels 6.7+ (Landlock ABI v4), TCP bind
  and connect, targeting ABI v9 with `--best-effort`; one secondary write-up describes the
  project as inactive from 2025-10 at ABI v5, which conflicts with the repository's stated
  target. FACT for the repository — https://github.com/Zouuup/landrun; the maintenance claim is
  one secondary source (https://rywalker.com/research/landrun) and is an open question for F2
  to settle from commit dates. Landlock is upstream from 5.13, network rules from 6.7. FACT —
  https://docs.kernel.org/security/landlock.html
- Apple's Containerization framework 1.0.0 (2026-06) runs each Linux container in its own
  lightweight VM on Apple Silicon with macOS 26. FACT — WWDC pages via
  https://appleinsider.com/2025/06/09. This machine is macOS 26.6 on Apple Silicon, so it is a
  candidate arm for the gold-tier container beside Docker and OrbStack.
- Bazel and Buck2 define hermeticity as no host, network or machine-state leakage and require
  remote execution for enforced sandboxing; neither models floating-point or CPU-feature drift.
  FACT for the hermeticity pages — https://bazel.build/basics/hermeticity ·
  https://www.tweag.io/blog/2023-07-06-buck2; the drift gap is INFERRED from absence. The §2
  numeric-profile field fills a gap the build systems leave open.

## 6. What changes, and what does not

Changes, each with an owner:

1. PLAN §16 operator defaults name Python 3.14 via uv as the coordination language with its
   revisit triggers; decision 13 states the authority-language rule; decision 14 makes the
   container digest input-addressed. Owner: this brief's commit.
2. PLAN §2 states that a skill's language is a property of its contract, with the identity
   fields a compiled skill fills. Owner: this brief's commit.
3. `MAP.md`: the system as one tower of layers, each with its authority language, identity
   primitive, record kinds, CLI verbs and gate, pinned by a test against the CLI registry and
   the claims kinds so it cannot rot. Owner: `MAP.md` here; the pinning test is a bead.
4. `cairn status --json`: one read-only call that renders the whole state and the affordances.
   Owner: a bead.
5. A unit tier of the suite under one minute, between `check.sh --fast` and the full run.
   Owner: a bead.
6. F2 (`cairn-m1-cqt.5.2`): input-addressed container identity, landrun maintenance settled
   from commit dates, Apple Containerization as a probed arm. Owner: a comment on that bead.
7. F5 (`cairn-m1-cqt.5.5`): the axiom set is computed Lean-side on the pinned toolchain and the
   `Lean.trustCompiler` and `sorryAx` refusals are planted fixtures. Owner: a comment on F5.

Not changed, with the reason: the harness language (no measured benefit, whole suite at
stake); the orchestrator's state layer (PLAN §12 and §15 P3 stand; DBOS-on-SQLite is named
as the M3 comparator spike, nothing more); MCP as a control surface for driving `cairn` (the
schema tax is paid on every prompt); Sage, PARI, SQLite, BLAKE3 and Lean 4 + mathlib as the
stack. Candidates recorded and unfunded: pytest-testmon on `src/cairn/skills/` once the unit
tier exists; a `concise|detailed` knob on `measure`, `selftest` and `doctor`; a single
close-verb script wrapping the mechanical close gates (`bead-test-plan.sh`,
`bead-artifact-block.sh`, the compliance audit) so a close is one command.

## 7. Open questions with owners

- CADO-NFS's DLP mode, FLINT 3.x's curve API, and any 2025–2026 ECDLP record: the research
  session that first needs index-calculus tooling (Mode E) settles them from primary sources.
- Whether `lean4-nix` can fold mathlib's olean cache into the closure: F2.
- Whether the comparator's statement check is structural equality on `ConstantVal` as the
  grounding brief's proxy assumes: F4 reads `Compare.lean` before hashing.
- Whether DBOS workflows can express runtime tree rewriting: M3's decomposition.
