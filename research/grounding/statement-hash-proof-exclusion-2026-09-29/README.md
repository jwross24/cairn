# Statement-hash proof exclusion probe

This probe measures preparation, not proof acceptance. Its contract is
[ADR-011](../../decisions/adr-011-statement-hash-excludes-proof-values.md).

## Reproduce the DLP measurement

From the checkout root, choose a nonexistent output directory beneath a scratch
directory. Lean and mathlib prerequisites must match the repository pins.

```sh
scratch=$(mktemp -d)
lockf -k /tmp/cairn-heavy.lock uv run --no-project python \
  /Users/jwross/.local/share/cairn-agent-mail/orders/memcap.py 6 \
  uv run python research/grounding/statement-hash-proof-exclusion-2026-09-29/measure.py \
  "$scratch/dlp" > "$scratch/dlp.log" 2>&1
```

`measurement.json` records the hasher source SHA-256, gate identity, pinned toolchain,
canonical byte count, closure constant count, byte digests and preparation time.
`canonical-output.json` and `canonical.bin` retain the emitted wire and canonical
bytes. The watchdog log supplies the descendant-tree physical-footprint peak.
The script validates frame boundaries and refuses a planted truncated frame.
`--item curve`, `--item curve_plus` and `--item finite` select the other inputs.

## Contract tests

```sh
lockf -k /tmp/cairn-heavy.lock uv run --no-project python \
  /Users/jwross/.local/share/cairn-agent-mail/orders/memcap.py 6 \
  uv run pytest -q -s tests/integration/test_hasher_stability.py
```

`properties.log` contains ten passing real Lean integration cases. The proof-only
pair changes `support` from a reference to `proofOnlyA` to `proofOnlyB`, with its
statement held fixed. Both its bytes and digest remain equal. Nested definition
values, opaque values and closure theorem types have sensitivity cases. The fresh
build pair compares exact bytes and digests across separate projects.

Each planted log records one scratch-copy mutation and the corresponding failed
byte assertion. The production file is unchanged by the mutation runs.

- `mutant-proof-value.log.gz`: `.thmInfo` includes `expr v.value`; the proof-only pair differs.
- `mutant-proof-traversal.log.gz`: `dependencies` traverses `.thmInfo` values; proof-only dependency names differ.
- `mutant-definition-value.log.gz`: `.defnInfo` omits `expr v.value`; the nested value pair collides.
- `mutant-theorem-type.log.gz`: `.thmInfo` retains only name and levels; the theorem-type pair collides.

The mutation driver runs the same integration test with a scratch hasher path
selected through `lean.STATEMENT_HASHER_PATH`, so the gate bundles the mutated
source. Each child exits 1 at the expected byte comparison; the driver exits 0
only when all four expected refusals occur. Compilation errors do not satisfy
this observation. Original scratch driver and sources are retained at
`/tmp/cairn-lane2-day.HCyLdO/run_mutants.py` and
`/tmp/cairn-lane2-day.HCyLdO/mutants/`.

## Evidence limits

`baseline-dlp.log` records the original hasher's full preparation failure at
6.70 GiB. `baseline-size.log` records a size-only encoder probe, not an emitted
8 GB artifact. `dlp.log` and `dlp-size.json` record the proof-excluding preparation
and the counts parsed from its emitted canonical bytes. Curve logs retain both
measured fixed digests. Timings describe this host and these inputs; they are not
thresholds for all mathematical statements. PROVEN still requires every independent
gate and statement-level review.
