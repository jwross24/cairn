Read this before editing CI lanes, `scripts/check.sh` lane wiring, or `.github/workflows/ci.yml` test jobs.

# CI lanes

The canonical lane list is code: `tests/_ci_lanes.py` (`CI_LANES`). `scripts/check.sh` prints the accepted names in its usage line.

CI runs one `scripts/check.sh --ci-lane <lane>` per lane:

`python`, `python-integration`, `m0-lineage`, `m0-replay`, `m0-transcript`, `m0-boundaries`, `gateplan`, `lean-core`, `lean-replay`, `solution`, `solution-library-dlp`, `solution-library-finite-point`, `solution-library-binding`, `solution-plan-exact`, `solution-plan-refusals`, `container`, `container-replay-exact`, `container-replay-refusals`, `container-plan-exact`, `container-plan-proven`, `container-plan-refusals`.

Their test sets are disjoint and exhaustive. With no lane argument the local check runs all 21 sets and requires Docker for the container tests.

Local aggregates, which CI does not call:

- `--ci-lane m0` runs the four M0 lanes.
- `--ci-lane lean` combines the core and fresh-replay cases.
- `--ci-lane solution-library` runs all three library cases.
- `--ci-lane solution-plan` runs all three ordered-plan cases in sequence.
- `--ci-lane container-replay` runs both container replay lanes.
- `--ci-lane container-plan` runs all three container ordered-plan and PROVEN lanes.
