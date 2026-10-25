#!/usr/bin/env bash
set -u

LIMIT_TOKENS=5000
LIMIT_BYTES=$((LIMIT_TOKENS * 4))

is_lockfile() {
	case "${1##*/}" in
		*.lock | *.lockb | package-lock.json | npm-shrinkwrap.json | pnpm-lock.yaml | go.sum) return 0 ;;
	esac
	return 1
}

is_generated() {
	git check-attr linguist-generated linguist-vendored -- "$1" | grep -qE ': (set|true)$'
}

binaries=$(git diff --cached --numstat --diff-filter=ACMR -z | tr '\0' '\n' | awk -F'\t' '$1 == "-" && $2 == "-" { print $3 }')

over=""
count=0
while IFS= read -r -d '' path; do
	# research/intake holds ledgers and records pinned by md5 elsewhere; splitting them breaks those references.
	case "$path" in research/intake/*) continue ;; esac
	is_lockfile "$path" && continue
	grep -qxF -- "$path" <<<"$binaries" && continue
	is_generated "$path" && continue
	bytes=$(git cat-file -s ":$path" 2>/dev/null) || continue
	if [ "$bytes" -gt "$LIMIT_BYTES" ]; then
		over="$over$(printf '  %s  %d tokens (%d bytes)' "$path" $((bytes / 4)) "$bytes")"$'\n'
		count=$((count + 1))
	fi
done < <(git diff --cached --name-only --diff-filter=ACMR -z)

[ "$count" -eq 0 ] && exit 0

cat >&2 <<EOF
pre-commit: $count staged file(s) exceed $LIMIT_TOKENS tokens (tokens = bytes / 4, so the limit is $LIMIT_BYTES bytes):

$over
Split each file listed above, then commit again:
  1. Find the seams. Group the file's functions, classes or sections by the one job each does
     (parsing, I/O, validation, rendering, CLI wiring, and so on).
  2. Move each group into its own file beside the original, named for that job
     (for example report.py becomes report_parse.py, report_render.py and report_cli.py).
     Aim for about 3,000 tokens (12,000 bytes) per file, so the next edit still fits.
  3. Keep the original path as the entry point. It imports and re-exports what callers use,
     so no import elsewhere has to change. Then shrink it to that wiring.
  4. Move the matching tests with the code: tests for report_parse.py go in test_report_parse.py.
  5. For Markdown or other prose, split on top-level headings into a folder with one file per
     section, and keep the original file as a short index that links to each part.
  6. For data or fixtures, write one file per case, or build the data inside the test.
  7. Run the tests, git add the new files and the shrunk original, and commit.

Lockfiles and binary files are skipped. A file a tool generates (codegen, vendored code) is
exempt once .gitattributes marks it "<path> linguist-generated". Mark only tool-written files
that way, never files a person or an agent writes by hand.
EOF
exit 1
