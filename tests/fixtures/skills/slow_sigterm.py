import os
import signal
import sys
import time

DELAY = float(os.environ.get("FIXTURE_SIGTERM_DELAY", "0.4"))


def main():
    sys.stdin.read()

    def unhurried(_signum, _frame):
        time.sleep(DELAY)
        sys.stdout.write('{"status":"OK"}\n')
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGTERM, unhurried)
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        time.sleep(0.01)
    return 0


if __name__ == "__main__":
    sys.exit(main())
