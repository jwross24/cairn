#!/usr/bin/env bash
# Prove a test detects a broken implementation: mutate, run, restore, verify.
# Exit 0 only when the mutation made the target go RED and the file came back byte-identical.
set -euo pipefail

usage() {
  cat <<'USAGE'
usage: mutation-check.sh <source-file> <old-text> <new-text> <pytest-target>...

Replaces one exact occurrence of <old-text> with <new-text> in <source-file>,
runs the pytest target(s), then restores the file and verifies the restore by
SHA-256. Reports how many tests the mutation killed.

exit 0  the mutation was killed (the run went red: a failure, a collection error, or a
        nonzero pytest exit with no recognized summary) and the restore is byte-identical
exit 1  the mutation SURVIVED - the target does not detect this defect
exit 2  usage error, anchor not unique, or restore mismatch

The verdict itself lives in scripts/mutation_verdict.py, which the suite exercises
directly: tests/conftest.py refuses a bash subprocess, so logic placed in this file
would be logic no test can reach.
USAGE
}

case "${1:-}" in -h|--help) usage; exit 0;; esac
[ $# -ge 4 ] || { usage >&2; exit 2; }

SRC="$1"; OLD="$2"; NEW="$3"; shift 3
[ -f "$SRC" ] || { echo "mutation-check: no such file: $SRC" >&2; exit 2; }

BACKUP="$(mktemp)"; SHA="$(mktemp)"
cp "$SRC" "$BACKUP"
shasum -a 256 "$SRC" > "$SHA"
restore() { cp "$BACKUP" "$SRC"; }
trap restore EXIT

COUNT="$(python3 - "$SRC" "$OLD" <<'PY'
import sys, pathlib
print(pathlib.Path(sys.argv[1]).read_text().count(sys.argv[2]))
PY
)"
[ "$COUNT" = "1" ] || { echo "mutation-check: anchor occurs $COUNT times, need exactly 1" >&2; exit 2; }

python3 - "$SRC" "$OLD" "$NEW" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace(sys.argv[2], sys.argv[3], 1))
PY

set +e
OUT="$(uv run pytest "$@" -q --no-header 2>&1)"
RC=$?
set -e

restore; trap - EXIT
shasum -a 256 -c "$SHA" >/dev/null || { echo "mutation-check: RESTORE MISMATCH on $SRC" >&2; exit 2; }

set +e
printf '%s\n' "$OUT" | uv run python "$(dirname "$0")/mutation_verdict.py" "$RC"
VERDICT=$?
set -e
exit "$VERDICT"
