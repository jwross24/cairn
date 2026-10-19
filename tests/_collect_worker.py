import contextlib
import io
import json
import sys

import pytest


def collect(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = int(pytest.main(argv))
    return {"returncode": code, "stdout": out.getvalue(), "stderr": err.getvalue()}


def main():
    protocol = sys.stdout
    sys.stdout = sys.stderr
    for line in sys.stdin:
        protocol.write(json.dumps(collect(json.loads(line))) + "\n")
        protocol.flush()


if __name__ == "__main__":
    main()
