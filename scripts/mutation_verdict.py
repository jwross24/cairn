"""The verdict half of scripts/mutation-check.sh: did the mutation make the target go red?

A test run goes red three ways, and only one of them is a `failed` count. A mutation that
breaks an import takes collection down (`1 error`), and a mutation that makes pytest itself
refuse prints no recognized summary at all while exiting nonzero. Both are detections.

Every decision lives here rather than in the shell: tests/conftest.py refuses a bash
subprocess, so logic placed there would be logic no test can reach.
"""

import re
import sys

SUMMARY_RE = re.compile(r"\b(\d+) (passed|failed|errors?)\b")


def summary_line(output):
    matched = [line for line in output.splitlines() if SUMMARY_RE.search(line)]
    return matched[-1].strip() if matched else ""


def red_count(line):
    return sum(int(count) for count, word in SUMMARY_RE.findall(line) if word != "passed")


def verdict(output, returncode):
    line = summary_line(output)
    red = red_count(line)
    if red:
        return True, f"KILLED  by {red} test(s): {line}"
    if returncode != 0:
        return True, f"KILLED  pytest exited {returncode}: {line or 'no recognized pytest summary line'}"
    return False, f"SURVIVED  the target does not detect this defect: {line}"


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
    killed, message = verdict(sys.stdin.read() if output is None else output, returncode)
    print(message)
    return 0 if killed else 1


if __name__ == "__main__":
    sys.exit(main())
