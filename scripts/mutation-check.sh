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

exit 0  the mutation was killed (>=1 test failed) and the restore is byte-identical
exit 1  the mutation SURVIVED - the target does not detect this defect
exit 2  usage error, anchor not unique, or restore mismatch
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
set -e
LINE="$(printf '%s\n' "$OUT" | grep -E '[0-9]+ (passed|failed)' | tail -1)"
KILLED="$(printf '%s\n' "$LINE" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || true)"

restore; trap - EXIT
shasum -a 256 -c "$SHA" >/dev/null || { echo "mutation-check: RESTORE MISMATCH on $SRC" >&2; exit 2; }

if [ -n "$KILLED" ] && [ "$KILLED" -gt 0 ]; then
  echo "KILLED  by $KILLED test(s): $LINE"
  exit 0
fi
echo "SURVIVED  the target does not detect this defect: $LINE"
exit 1
