import os
import signal
import sys
import time
from pathlib import Path

SEEN = "sigterm_seen"


def main():
    sys.stdin.read()
    scratch = sys.argv[1]

    def note(_signum, _frame):
        with (Path(scratch) / SEEN).open("w") as handle:
            handle.write("term")
        sys.stdout.write('{"status":"OK"}\n')
        sys.stdout.flush()
        os._exit(0)

    signal.signal(signal.SIGTERM, note)
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        time.sleep(0.01)
    return 0


if __name__ == "__main__":
    sys.exit(main())
