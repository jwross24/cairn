import os
import subprocess
import sys
import time


def main():
    sys.stdin.read()
    scratch = sys.argv[1]
    marker = os.path.join(scratch, "grandchild")
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"import time; open({marker!r}, 'w').write('x'); time.sleep(30)",
        ]
    )
    with open(os.path.join(scratch, "grandchild_pid"), "w") as handle:
        handle.write(str(child.pid))
    if os.environ.get("FIXTURE_REAP") == "1":
        child.wait()
    time.sleep(30.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
