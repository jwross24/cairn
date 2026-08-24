import signal
import sys
import time


def main():
    sys.stdin.read()
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        time.sleep(0.01)
    return 0


if __name__ == "__main__":
    sys.exit(main())
