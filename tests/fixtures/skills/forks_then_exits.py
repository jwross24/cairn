import subprocess
import sys
from pathlib import Path


def main():
    sys.stdin.read()
    scratch = sys.argv[1]
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    with (Path(scratch) / "grandchild_pid").open("w") as handle:
        handle.write(str(child.pid))
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
