# ADR 011: Statement identity excludes theorem proof values

## Status

Accepted on 2026-09-29 by MagentaSparrow under the operator's delegated authority,
agent-mail message 209, bead `cairn-u5qo`.

## Decision

The formal statement hash includes each target theorem's name, level parameters and
type. Its sorted transitive closure includes constant types and the values of
definitions and opaque constants. A theorem in that closure contributes only its
name, level parameters and type. Neither serialization nor dependency traversal
includes theorem proof values. Structural metadata for other declaration kinds,
including inductive constructors and recursor rules, retains its canonical encoding.

The hash names and binds a statement. Kernel replay, the axiom set and comparator
check (iv) decide acceptance. A hash match with a comparator mismatch fails closed.
This decision does not alter those checks, statement-level match review, calibration
tags, or the requirements for PROVEN.

## Rationale

Proof irrelevance separates what a theorem asserts from its proof. Definition values
affect what a statement means and therefore belong in its identity. PLAN §7 identifies
the closure definition as a conjecture requiring an M1 probe, rather than a proof
acceptance rule. The operator's decision settles that identity question.

The proof-inclusive DLP size probe reports 8,070,948,074 canonical bytes across 22,337
closure constants. Its largest record, `WeierstrassCurve.Affine.addPolynomial_slope`,
is 1,265,744,684 bytes. Full DLP preparation with the original hasher exceeds the
6 GiB physical-footprint cap and is killed at 6.70 GiB. That result establishes a
preparation failure, not a defect in the mathematical statement.

A representation-preserving streaming encoder would retain that closure and its
serialization cost. Excluding proof values addresses the statement-identity boundary.
Streaming requires separate justification if this closure cannot fit the cap.

## Contract properties

- A definition value change anywhere in the closure changes the hash.
- A closure theorem's statement change changes the hash.
- A change confined to a closure theorem's proof leaves canonical bytes unchanged,
  including when the proofs reference different proof-only dependencies.
- Two runs over the same input produce identical canonical bytes.

The raw hasher source is an identity-bearing gate-bundle object. This definition
requires reviewed formal-statement and bundle golden digests; it provides no decoder
that treats distinct definitions as the same identity. M1 has no PROVEN claims or
downstream consumers requiring compatibility.

## Measurement provenance

The original hasher source SHA-256 is
`c2840ef56a0a32d015571041a74617dd415ed7c76f411dabe9515f5442b744a0`.
The toolchain is Lean `v4.34.0-rc1`, with mathlib
`1f29011071772620f612bf5a06433775f06067b8`.
The DLP statement is `cairn_dlp_iff` in `lean/Library/Dlp/Statement.lean`.
Raw baseline logs are retained at
`/tmp/cairn-lane2-day.HCyLdO/baseline-dlp-tree.log`,
`/tmp/cairn-lane2-day.HCyLdO/dlp-size.log` and
`/tmp/cairn-lane2-day.HCyLdO/dlp-record-size.log`.
The size probe computes framed lengths without emitting the complete canonical
string; the full baseline emits no completed canonical artifact.

The proof-excluding hasher, source SHA-256
`3e45c126050d8d54e2e7c28f1f7937147d8d24d57fa2b6babbec84568501882f`,
prepares the DLP Challenge through `solutionchecks.prepare_dev` in 38.1026 seconds
under its default 600-second bound. The descendant-tree watchdog reports a peak
physical footprint of 0.51 GiB with a 6 GiB cap. The emitted canonical bytes number
4,985,420 across 1,217 closure constants; the largest record is 131,354 bytes.
Streaming is unnecessary for this measured input.

The formal statement digest is
`deba336e535bd991820a8790fb7ed0dc4a88f60fd20c44b74e806590bfb789a0`.
Canonical SHA-256 is
`f404758266cf33706e3d83a44a5f898c5ea7cc3e98309da5af560b2c006cefa1`.
Raw output and parsed framing counts are retained at
`/tmp/cairn-lane2-day.HCyLdO/owner209-dlp.log`,
`/tmp/cairn-lane2-day.HCyLdO/owner209-dlp/canonical-output.json` and
`/tmp/cairn-lane2-day.HCyLdO/owner209-dlp-size.json`.
These observations establish preparation cost for this input and pinned toolchain,
not a universal memory bound or mathematical acceptance.

Tracked raw evidence resides in
[`statement-hash-proof-exclusion-2026-09-29`](../grounding/statement-hash-proof-exclusion-2026-09-29/).
`properties.log` records ten passing integration cases. Each `mutant-*.log.gz` records
one expected assertion failure: adding proof serialization, adding proof dependency
traversal, omitting definition values, or omitting closure theorem types. The
failures occur at canonical-byte comparisons, with both variants' digests and byte
SHA-256 values printed. Compilation failure is not counted as a planted refusal.

The curve fixture `W.Δ = W.Δ` has formal digest
`050203449ae9ec911926c65bcbb8786f41e86730ca16b2427bb240662b0b2b4d`;
the `W.Δ + 0 = W.Δ` variant has digest
`928724caf7b2404b9a79315dc4bb8f65b999726d71a21f212d657ac2d5d490e4`.
Their preparation runs take 35.8235 and 47.8060 seconds, with physical-footprint
peaks of 0.53 and 0.56 GiB. The `ConstantVal` framing known-answer vector in
`tests/goldens/formal_statement.golden` is independent of closure traversal and
retains its bytes. The reviewed gate bundle digest is
`3320a78917bb401911afdf63f140b7829e1c8f297b955d8eb00c3b5263075c65`,
including the nanoda configuration from `fe80638`.

The tracked measurement script's independent run takes 38.3809 seconds at a
0.50 GiB physical-footprint peak. `dlp-repeat.json` records exact equality of
the two 9,970,861-byte wire outputs and their SHA-256 values; both runs also
produce the same canonical digest. `measurement.json` contains the source,
toolchain and bundle identities for that run.

The real Linux hash-pair/missing-theorem test and preparation without host Lean
both pass in 112.19 seconds. Their 17 container invocations carry `--memory=6g`
and `--memory-swap=6g`; the host process-tree peak is 0.23 GiB. `linux.log` and
`linux-cap.json` retain the results and exact image ID. Container memory limits
are distinct from the host watchdog's footprint measurement.
