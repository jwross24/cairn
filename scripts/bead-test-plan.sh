#!/usr/bin/env bash
# A bead's body names the test files it will produce. This checks that each one
# exists and that pytest actually collects tests from it, so a bead cannot close
# claiming a test plan nobody wrote.
#
#   scripts/bead-test-plan.sh <bead-id> [<bead-id> …]
#
# Consumer: the session closing the bead, and the pre-commit hook, which runs it
# for every bead a commit closes. It gates the close. The observed defect it
# exists for: the compliance audit reported cairn-m0-e0s.12's integration, e2e,
# fuzz and metamorphic tests as MISSING while all but the e2e one were present,
# and nothing in the repo could settle which reading was right.
#
# Retire it when the compliance skill's evidence gatherer attributes test files
# to their declared test types on its own.
#
# Bypass, named and logged to .check.log: CAIRN_TEST_PLAN_SKIP='<reason>'
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 3
LOG="$ROOT/.check.log"
say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG"; }

if [ $# -eq 0 ]; then
  echo "usage: scripts/bead-test-plan.sh <bead-id> [<bead-id> …]" >&2
  exit 64
fi

if [ -n "${CAIRN_TEST_PLAN_SKIP:-}" ]; then
  say "BYPASS test-plan $*: $CAIRN_TEST_PLAN_SKIP"
  echo "[test-plan] BYPASSED: $CAIRN_TEST_PLAN_SKIP (logged to .check.log)" >&2
  exit 0
fi

for tool in br uv; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    say "DENY test-plan infra: $tool not on PATH"
    echo "[test-plan] $tool is not installed; refusing to report a plan as met without checking it." >&2
    exit 3
  fi
done

STATUS=0
for BID in "$@"; do
  PATHS="$(br show "$BID" --json 2>/dev/null | uv run python -c '
import json, re, sys
raw = json.load(sys.stdin)
rows = raw if isinstance(raw, list) else raw.get("issues", [raw])
while isinstance(rows, list) and rows and isinstance(rows[0], list):
    rows = rows[0]
row = rows[0] if isinstance(rows, list) else rows
body = " ".join(str(row.get(f) or "") for f in ("description", "acceptance_criteria", "notes", "design"))
print(row.get("status") or "unknown")
print("\n".join(sorted(set(re.findall(r"tests/[\w./-]+\.py", body)))))
')"

  BEAD_STATUS="$(printf '%s\n' "$PATHS" | head -1)"
  PATHS="$(printf '%s\n' "$PATHS" | tail -n +2)"

  if [ -z "$PATHS" ]; then
    say "SKIP test-plan $BID: the body names no test file"
    echo "[test-plan] $BID names no test file; nothing to check."
    continue
  fi

  MISSING=()
  EMPTY=()
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    if [ ! -f "$rel" ]; then
      MISSING+=("$rel")
      continue
    fi
    # Only a test module owes tests. A bead may also name factories, fixtures and
    # mutant catalogs, which exist to be imported and collect nothing by design.
    case "$(basename "$rel")" in
      test_*.py|*_test.py)
        if ! uv run pytest --collect-only -q "$rel" >/dev/null 2>&1; then
          EMPTY+=("$rel")
        fi
        ;;
    esac
  done <<< "$PATHS"

  if [ ${#MISSING[@]} -eq 0 ] && [ ${#EMPTY[@]} -eq 0 ]; then
    say "PASS test-plan $BID ($(echo "$PATHS" | grep -c .) file(s))"
    echo "[test-plan] pass $BID ($BEAD_STATUS): every named test file exists, and every test module collects"
    continue
  fi

  STATUS=1
  say "FAIL test-plan $BID status=$BEAD_STATUS missing=${MISSING[*]:-none} uncollectable=${EMPTY[*]:-none}"
  echo "[test-plan] FAIL $BID (status=$BEAD_STATUS)" >&2
  for rel in "${MISSING[@]:-}"; do [ -n "$rel" ] && echo "            named but absent:       $rel" >&2; done
  for rel in "${EMPTY[@]:-}"; do [ -n "$rel" ] && echo "            present but collects nothing: $rel" >&2; done
done

if [ $STATUS -ne 0 ]; then
  echo "            write the missing tests, or correct the bead body if the plan changed." >&2
  echo "            bypass (logged): CAIRN_TEST_PLAN_SKIP='<reason>'" >&2
fi
exit $STATUS
