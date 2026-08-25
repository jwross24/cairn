import os
import subprocess
import sys


def main():
    sys.stdin.read()
    if os.environ.get("FIXTURE_GRANDCHILD") == "1":
        subprocess.run([sys.executable, "-c", "x = 0\nfor i in range(9_000_000): x += i"])
    total = 0
    for i in range(2_000_000):
        total += i
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
