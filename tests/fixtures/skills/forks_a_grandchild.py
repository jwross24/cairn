import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    sys.stdin.read()
    scratch = sys.argv[1]
    marker = str(Path(scratch) / "grandchild")
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"import time; open({marker!r}, 'w').write('x'); time.sleep(30)",
        ]
    )
    with (Path(scratch) / "grandchild_pid").open("w") as handle:
        handle.write(str(child.pid))
    if os.environ.get("FIXTURE_REAP") == "1":
        child.wait()
    time.sleep(30.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
