import os
import subprocess
import sys
import time


def main():
    sys.stdin.read()
    subprocess.Popen([sys.executable, "-c", "x = 0\nfor i in range(40_000_000): x += i"])
    if os.environ.get("FIXTURE_OUTLIVE") == "1":
        time.sleep(30.0)
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
