# cairn's gates against the record

Read in the cairn tree, 2026-10-30. Paths are at the commit this note landed in.

## Reviewer isolation: mechanical
`src/cairn/worker.py:28-47` launches the Skeptic with `tools=[]`, `skills=[]`, `setting_sources=[]`,
`strict_mcp_config=True`, `permission_mode="dontAsk"`, and `--bare`, `--disable-slash-commands`,
`--no-session-persistence`. `_validate_init` (`worker.py:74-91`) refuses a run whose initialized tools, MCP servers,
skills, plugins, slash commands, memory paths or cwd differ from the dispatch. `bundle/worker_roles.json` grants only
`list_nodes` and `read_node` over canonical typed nodes scoped by `bundle/skeptic_scope.json`
(`src/cairn/skeptic.py`, `ScopedReadRefused`). PLAN.md: the Skeptic "sees only the *statement*, never the prover's
reasoning"; "independence is the whole value."
This answers the dataroom's open question: isolation is by construction, not by declaration. It is stronger than the
KLS template's self-declaration. Palomar adds an OS namespace; cairn has no process sandbox here, but the worker has
no filesystem or shell tool to reach anything with.

## Statement review: human, typed, bound to the hash
PLAN.md (Statement-level review): `review_verdict {statement hash, reviewer, verdict, checklist template hash,
gate-bundle hash, time, supersedes?}`, immutable, written only by the human path, "never by a worker or the
orchestrator"; "a verdict names one statement hash and does not transfer to a superseding version"; `justify` derives
PROVEN only from a `lean_artifact` and an `approve` verdict on the same hash. Prefilters "reject or flag, never pass",
including a vacuity check. This covers the seam Palomar's prompt names, and the KLS failure mode.

## Two kernels: yes
`bundle/lean.json:3` sets `"external_kernels": {"nanoda": ["/usr/local/bin/nanoda_bin"]}`, passed to the comparator
config at `src/cairn/solutionbuild.py:292`. So a proof must pass the pinned official kernel and nanoda.

## Kernel exposure, corrected
- Official kernel: `v4.34.0-rc1` lacks #14582, #14806, #14807, #14808, #14843 (`notes/lean-kernel-postmortems.md`).
- nanoda: `bundle/container.json` pins `3a24072` (2026-09-22), 7 commits past `4c544ed`, the version the arena's
  2026-09 round scored at 71 of 71 invalid proofs rejected, and it contains `nanoda_lib#22`.
- So the arena's invalid proofs that rc1 may accept are rejected by nanoda, on the arena's evidence. A proof of `False`
  through this gate needs a second, independent bug in pinned nanoda: the shape of Kumar's exploit, not a free pass.
- That residual is real. The pin is 33 commits behind nanoda HEAD, including `check proj ty_name as other kernels do`
  (2026-10-12), `validate restored recursor in current env` (2026-10-23) and `harden Quot and unique temp name checks`
  (2026-10-27). Whether any is a soundness fix for a reachable bug is not established. Lean's postmortem also records
  nanoda accepting the #14807 bogus proof in August; whether the arena's `bugs/` suite encodes that exploit is not
  established, and arena verdicts are per test, not a proof of absence.
- A wrinkle: a bump of the toolchain fixes the first kernel only; both pins must move together.

## Gaps the record exposes
1. Both kernel pins lag their fixes (cairn-p76j).
2. No literature or novelty check; "already known" is the costliest verdict in the Erdős census.
3. Citations pass through no gate.
4. A two-kernel gate is the configuration Kumar beat; v4.35.0's `--paranoid` runs five (cairn-2k8k).

## The post-pin nanoda holes (read 2026-10-30)
Three arena `bugs/` tests added after cairn's nanoda pin (2026-09-22) are axiom-free proofs of `False` that nanoda
accepted until fixed:
- `nested-rec-rule-nfields` (added 2026-10-23): a recursor rule of a nested inductive lies about its field count;
  "Nanoda validated the rules of non-nested inductives, but not of nested ones, until it was fixed" (nanoda_lib#60).
- `forged-quot-ind` (2026-10-27): a hand-written export declares `Quot.ind` before `Quot` and `Quot.mk`. "The official
  kernel installs the quotient declarations together and rejects the file."
- `nested-name-capture` (2026-10-27): a later definition takes the name of a temporary `_nested.*.rec`. "The official
  kernel rejects the file." rc1 carries #14616 (reject declarations naming `_nested` auxiliary types).
All found by "a differential run of Pestka against other checkers": new kernels are still finding bugs in old ones.

The gate is an intersection, so what decides exposure is whether a proof passes BOTH pinned kernels:
- `forged-quot-ind` and `nested-name-capture`: the official kernel rejects them, so they should stop at rc1. Not run.
- `nested-rec-rule-nfields`: pinned nanoda accepts (by the test's own history). Whether rc1 rejects it is not
  established, and rc1 lacks #14808, which type-checks generated recursors. This is the one to run first.
- In the other direction, rc1's own bugs (#14806, #14807) were each tested against nanoda only at the time of the
  postmortem, and nanoda accepted the #14807 exploit then.
So the intersection is untested. No claim that a proof of `False` passes cairn's gate is established, and none that it
cannot. Only running both pinned kernels on the arena suite settles it; that is AC 1 of cairn-p76j.
