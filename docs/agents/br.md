Read this before closing a bead (the `check` gate), upgrading `br`, editing `BR_VERSION` in `ci.yml`, changing `scripts/beads_doctor_gate.py`, or when `br` reports a schema or asset error.

# br release lines, schema and doctor detail

- Current: `br` 0.7.6, tracker schema 19. `ci.yml` carries the matching `BR_VERSION`.
- Asset names: 0.2, 0.6 and 0.7.x publish `br-<version>-<os>_<arch>.tar.gz` (`darwin_arm64`, `linux_arm64`, `linux_amd64`). 0.5 published `beads_rust-` with `aarch64` on Linux. A version bump across a line that changed the name 404s when the name is left alone.
- `br show --json` is identical in shape and value between 0.5.7 and 0.6.0.
- A schema-17 store is migrated with `br doctor migrate-schema plan`, then `apply --plan-token`. Ordinary commands refuse it with `SCHEMA_MISMATCH`.
- An empty schema-10 store is parked at `~/.beads.stale-2026-09-02`. A `br` error naming schema 17 against 10 means such a store is on the walk-up path again. `br` walks upward for a workspace, so a command run while the repo's `.beads` is absent, or from another directory such as the vault, binds to whatever store sits on that path.
- Mixed versions: a 0.6.0 writer and a 0.7.x writer on one tracker can leave the JSONL export refused until `br sync --flush-only` runs.
- Doctor gate: `scripts/beads_doctor_gate.py` accepts the statuses `ok` and `warn` as benign, the workspace labels `healthy` and `degraded`, and a verdict of advisory with no blocking findings. It hard-codes no per-status counts.
- Argument syntax: text arguments starting with `-` need the `=` form (`--description=`, `--notes=`, `--design=`, `--acceptance-criteria=`). `br create` takes `--description`/`-d` only; acceptance criteria are set afterward with `br update <id> --acceptance-criteria=...`.
- JSON shapes: `br show --json` returns an array (index `.[0]`); `br list --json` returns `{"issues": [...], "has_more": ...}` and omits closed beads without `--all`. Tombstones appear only in `issues.jsonl`.
- `br doctor` first; `beads.db` is derived state: move it aside and `br sync --import-only` rebuilds it. The real health check is `sqlite3 .beads/beads.db "PRAGMA integrity_check"`.

# The check gate on a close

`.beads/policy.yaml` refuses `in_progress -> closed` until the bead's `check` gate has a pass (ADR-017). The usual reporter is CI's run on the pushed closing commit:

1. Commit the bead's work and push it; `git status` shows up to date with `origin/main`.
2. Wait for the `ci.yml` push run on that commit to finish green (`gh run list --workflow ci.yml --commit "$(git rev-parse HEAD)"`).
3. `scripts/check.sh --from-ci --bead <id>` records the pass with provider `ci`, or names why it cannot in a `DENY gate-report` line in `.check.log`: `ci-not-pushed`, `ci-not-green`, `ci-lane-missing` or `ci-unanswered`.
4. `br close <id> --reason "..."`; the close record rides with the next commit.

For a commit CI cannot run, the full local `scripts/check.sh --bead <id>` (every lane, Docker) reports the gate instead.
