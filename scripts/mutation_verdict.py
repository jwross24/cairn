"""The verdict half of scripts/mutation-check.sh: did the mutation make the target go red?

A test run goes red two ways that are both detections: a `failed` count, and a mutation
that breaks an import and takes collection down (`1 error`). Either one is a red count on
the summary line, and pytest's own exit code 1 says the same thing when the summary is
unreadable.

Pytest's other nonzero codes say the opposite. 2 is an interruption, 3 an internal error,
4 a usage error and 5 no tests collected: in every one of those the target never ran, so
the mutation was never put to any test. Those are INCONCLUSIVE, and reading them as a
detection tells a reader a suite with no coverage at all is fully gated.

Every decision lives here rather than in the shell: tests/conftest.py refuses a bash
subprocess, so logic placed there would be logic no test can reach.
"""

import re
import sys

SUMMARY_RE = re.compile(r"\b(\d+) (passed|failed|errors?)\b")

KILLED = "KILLED"
SURVIVED = "SURVIVED"
INCONCLUSIVE = "INCONCLUSIVE"

PYTEST_TESTS_FAILED = 1
EXIT_BY_VERDICT = {KILLED: 0, SURVIVED: 1, INCONCLUSIVE: 3}


def summary_line(output):
    matched = [line for line in output.splitlines() if SUMMARY_RE.search(line)]
    return matched[-1].strip() if matched else ""


def red_count(line):
    return sum(int(count) for count, word in SUMMARY_RE.findall(line) if word != "passed")


def verdict(output, returncode):
    line = summary_line(output)
    red = red_count(line)
    seen = line or "no recognized pytest summary line"
    if red:
        return KILLED, f"KILLED  by {red} test(s): {line}"
    if returncode == PYTEST_TESTS_FAILED:
        return KILLED, f"KILLED  pytest exited {returncode}: {seen}"
    if returncode != 0:
        return INCONCLUSIVE, (
            f"INCONCLUSIVE  pytest exited {returncode} without testing the mutation: {seen}. "
            "Exit 2 is an interruption, 3 an internal error, 4 a usage error and 5 no tests "
            "collected; name the target explicitly, one argument per target, and run it again."
        )
    return SURVIVED, f"SURVIVED  the target does not detect this defect: {line}"


def main(argv=None, output=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if len(argv) != 1:
        print("usage: mutation_verdict.py <pytest-returncode>  (pytest output on stdin)", file=sys.stderr)
        return 2
    try:
        returncode = int(argv[0])
    except ValueError:
        print(f"mutation_verdict: {argv[0]!r} is not a return code", file=sys.stderr)
        return 2
    outcome, message = verdict(sys.stdin.read() if output is None else output, returncode)
    print(message)
    return EXIT_BY_VERDICT[outcome]


if __name__ == "__main__":
    sys.exit(main())
