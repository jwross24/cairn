# Walk code_artifacts
while IFS= read -r item; do
  ITEM_ID="$(printf '%s' "$item" | jq -r '.id')"
  HINTS="$(printf '%s' "$item" | jq -r '.expected_path_hints[]?' 2>/dev/null || true)"
  CITATIONS="[]"
  STATUS="MISSING"
  NOTES=""
  while IFS= read -r hint; do
    [ -n "$hint" ] || continue
    resolved="$(resolve_path_hint "$hint")"
    if [ -n "$resolved" ]; then
      # Find the commit that last modified it
      COMMIT="$(git -C "$PROJECT" log -n1 --format=%H -- "$resolved" 2>/dev/null || echo unknown)"
      # `wc -l < <directory>` errors out and the failure can leave LINES
      # empty, which then makes `--argjson e "$LINES"` raise
      # `jq: invalid JSON text passed to --argjson` and `set -e` kills the
      # script. Detect file vs directory explicitly and zero LINES for any
      # non-file (directory citations are common when a bead names a path
      # like `src/indexer/` rather than a single file). A final defense
      # against any remaining edge case: coerce empty/non-numeric to 0.
      if [ -f "$PROJECT/$resolved" ]; then
        LINES="$(wc -l < "$PROJECT/$resolved" 2>/dev/null || echo 0)"
      else
        LINES=0
      fi
      [[ "$LINES" =~ ^[0-9]+$ ]] || LINES=0
      CITATIONS="$(printf '%s' "$CITATIONS" | jq --arg p "$resolved" --arg c "$COMMIT" --argjson e "$LINES" \
        '. + [{path: $p, line_start: 1, line_end: $e, commit_sha: $c, via: "expected_path_hints"}]')"
      STATUS="FOUND"
    fi
  done <<< "$HINTS"
  if [ "$STATUS" = "MISSING" ]; then
    NOTES="No file matched any of: $HINTS"
  fi
  emit_check "$ITEM_ID" "$STATUS" "$NOTES" "$CITATIONS"
done < <(jq -c '.checklist.code_artifacts[]?' "$SPEC")

# Walk tests (each type)
for ttype in unit integration e2e fuzz property metamorphic golden conformance; do
  while IFS= read -r item; do
    ITEM_ID="$(printf '%s' "$item" | jq -r '.id')"
    DESC="$(printf '%s' "$item" | jq -r '.description // ""')"
    CITATIONS="[]"
    STATUS="MISSING"
    # Heuristic: search for the test name (id) in the project
    NAME="$(printf '%s' "$ITEM_ID" | sed 's/.*\.//')"
    if [ -n "$NAME" ] && [ "$NAME" != "primary" ]; then
      MATCHES="$(rg -F -l --no-heading -- "$NAME" "$PROJECT" 2>/dev/null | head -3 || true)"
      while IFS= read -r f; do
        [ -n "$f" ] || continue
        rel="${f#"$PROJECT"/}"
        CITATIONS="$(printf '%s' "$CITATIONS" | jq --arg p "$rel" \
          '. + [{path: $p, line_start: 1, line_end: 1, commit_sha: "unknown", via: "rg test name"}]')"
        STATUS="FOUND"
      done <<< "$MATCHES"
    fi
    emit_check "$ITEM_ID" "$STATUS" "type=$ttype desc=$DESC" "$CITATIONS"
  done < <(jq -c --arg ttype "$ttype" '.checklist.tests[$ttype][]?' "$SPEC")
done

# Walk documentation / migrations / feature_flags / telemetry / ci_workflows
for cat in documentation migrations feature_flags telemetry ci_workflows; do
  while IFS= read -r item; do
    ITEM_ID="$(printf '%s' "$item" | jq -r '.id')"
    CITATIONS="[]"
    STATUS="MISSING"
    case "$cat" in
      documentation)
        if [ -f "$PROJECT/README.md" ]; then
          STATUS="FOUND"
          CITATIONS='[{"path":"README.md","line_start":1,"line_end":1,"via":"file existence"}]'
        fi ;;
      ci_workflows)
        if [ -d "$PROJECT/.github/workflows" ]; then
          STATUS="FOUND"
          CITATIONS='[{"path":".github/workflows/","line_start":1,"line_end":1,"via":"directory existence"}]'
        fi ;;
    esac
    emit_check "$ITEM_ID" "$STATUS" "category=$cat" "$CITATIONS"
  done < <(jq -c --arg cat "$cat" '.checklist[$cat][]?' "$SPEC")
done
