#!/usr/bin/env bash
# The one place that says what "green" means. The pre-commit hook and CI both
# call this, so a gate can never be enforced in one and absent from the other.
#
#   scripts/check.sh --fast   format + lint + spelling   (seconds; the hook)
#   scripts/check.sh          the above plus the suite   (minutes; CI)
#   scripts/check.sh --fast --paths <p> ...   the same gates over those paths alone
#
# Without --paths every gate has the scope it always had, which is the form CI runs.
# With --paths the gates are scoped to that list, so one lane's red file in the working
# tree cannot refuse another lane's commit; the tree-wide catch is CI's. A gate with no
# path in its scope is skipped by name: ruff over an empty argument list widens back to
# the whole tree, which would report a pass for a scope nobody checked.
#
# Every run appends one line per gate to .check.log with pass/fail/skip, so a
# reader can tail it and see what actually fired. A gate whose tool is missing
# DENIES; it never passes quietly.
#
# Bypass, named and logged: CAIRN_CHECK_SKIP='<reason>' scripts/check.sh
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 3
LOG="$ROOT/.check.log"
STAMP() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { printf '%s %s\n' "$(STAMP)" "$*" >> "$LOG"; }

if [ -n "${CAIRN_CHECK_SKIP:-}" ]; then
  say "BYPASS all gates: $CAIRN_CHECK_SKIP"
  echo "[check] BYPASSED: $CAIRN_CHECK_SKIP (logged to .check.log)" >&2
  exit 0
fi

FAST=0
UNIT=0
SCOPED=0
PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --fast) FAST=1; shift ;;
    --unit) UNIT=1; shift ;;
    --paths) SCOPED=1; shift; PATHS=("$@"); break ;;
    *)
      say "DENY usage: unknown argument $1"
      echo "[check] unknown argument: $1" >&2
      echo "        usage: scripts/check.sh [--fast|--unit] [--paths <path> ...]" >&2
      exit 3
      ;;
  esac
done

if ! command -v uv >/dev/null 2>&1; then
  say "DENY infra: uv not on PATH"
  echo "[check] uv is not installed; every gate runs through it." >&2
  echo "        install: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 3
fi

FAILED=()

# Output streams rather than being captured. A captured gate that hangs prints
# nothing at all, which is how a 45-minute CI hang produced no diagnostic beyond
# the step before it.
gate() {
  local name="$1"; shift
  say "RUN $name"
  printf '[check] run %s\n' "$name"
  if ! "$@"; then
    say "FAIL $name"
    printf '[check] FAIL %s\n' "$name" >&2
    FAILED+=("$name")
    return 1
  fi
  say "PASS $name"
  printf '[check] pass %s\n' "$name"
}

scoped_gate() {
  local name="$1"; shift
  local count="$1"; shift
  if [ "$count" -eq 0 ]; then
    say "SKIP $name (no path in its scope)"
    printf '[check] skip %s (no path in its scope)\n' "$name"
    return 0
  fi
  gate "$name" "$@"
}

if [ "$SCOPED" = "1" ]; then
  PLAN="$(mktemp)"
  uv run python scripts/gate_scope.py plan --root "$ROOT" -- ${PATHS[@]+"${PATHS[@]}"} > "$PLAN"
  PLAN_RC=$?
  if [ "$PLAN_RC" -ne 0 ]; then
    say "DENY scope: gate_scope.py plan exited $PLAN_RC"
    echo "[check] the scoped path list is unusable; no gate ran." >&2
    echo "        usage: scripts/check.sh [--fast|--unit] [--paths <path> ...]" >&2
    exit 3
  fi
  FORMAT_ARGS=(); LINT_ARGS=(); SPELLING_ARGS=(); TYPES_ARGS=(); THEATER_ARGS=()
  while IFS="$(printf '\t')" read -r scope_gate scope_path; do
    case "$scope_gate" in
      format)   FORMAT_ARGS+=("$scope_path") ;;
      lint)     LINT_ARGS+=("$scope_path") ;;
      spelling) SPELLING_ARGS+=("$scope_path") ;;
      types)    TYPES_ARGS+=("$scope_path") ;;
      theater)  THEATER_ARGS+=("$scope_path") ;;
    esac
  done < "$PLAN"
  say "SCOPE ${#PATHS[@]} paths: format=${#FORMAT_ARGS[@]} lint=${#LINT_ARGS[@]} spelling=${#SPELLING_ARGS[@]} types=${#TYPES_ARGS[@]} theater=${#THEATER_ARGS[@]}"
  scoped_gate format   ${#FORMAT_ARGS[@]}   uv run ruff format --check ${FORMAT_ARGS[@]+"${FORMAT_ARGS[@]}"}
  scoped_gate lint     ${#LINT_ARGS[@]}     uv run ruff check ${LINT_ARGS[@]+"${LINT_ARGS[@]}"}
  scoped_gate spelling ${#SPELLING_ARGS[@]} uv run codespell ${SPELLING_ARGS[@]+"${SPELLING_ARGS[@]}"}
  scoped_gate types    ${#TYPES_ARGS[@]}    uv run ty check ${TYPES_ARGS[@]+"${TYPES_ARGS[@]}"}
  scoped_gate theater  ${#THEATER_ARGS[@]}  ./scripts/theater-patterns.sh ${THEATER_ARGS[@]+"${THEATER_ARGS[@]}"}
else
  gate format   uv run ruff format --check src tests scripts
  gate lint     uv run ruff check src tests scripts
  gate spelling uv run codespell
  gate types    uv run ty check src tests
  gate theater  ./scripts/theater-patterns.sh
fi
if [ "$FAST" = "1" ]; then
  say "SKIP tests (--fast)"
  printf '[check] skip tests (--fast; CI runs them)\n'
elif [ "$UNIT" = "1" ]; then
  gate unit-tests uv run pytest tests/unit -q -m "not slow" --durations=10
else
  if [ -n "${CAIRN_SESSION_DEADLINE_SKIP:-}" ]; then
    say "DEADLINE bypassed: $CAIRN_SESSION_DEADLINE_SKIP"
  else
    say "DEADLINE ${CAIRN_SESSION_DEADLINE:-3000}s session (dumps every thread; a kill prints 'Timeout (' on stderr, and the watchdog exits 124, its faulthandler backstop 15s later exits 1; an in-process libpari call past cairn.pari.CALL_BOUND_S prints 'libpari stall in <test>' and also exits 124)"
  fi
  gate tests uv run pytest -q --durations=25
fi

if [ ${#FAILED[@]} -ne 0 ]; then
  say "RESULT fail: ${FAILED[*]}"
  printf '\n[check] FAILED: %s\n' "${FAILED[*]}" >&2
  printf '        fix formatting: uv run ruff format src tests scripts\n' >&2
  printf '        fix lint:       uv run ruff check --fix src tests scripts\n' >&2
  printf '        bypass (logged): CAIRN_CHECK_SKIP=%s scripts/check.sh\n' "'<reason>'" >&2
  exit 1
fi

say "RESULT pass (fast=$FAST unit=$UNIT scoped=$SCOPED)"
printf '[check] all gates pass\n'
