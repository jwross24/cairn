import os
import sys
from pathlib import Path


def main():
    sys.stdin.read()
    scratch = Path(sys.argv[1])
    outside = scratch.parent.parent / "outside_secret.txt"
    outside.write_bytes(b"OUTSIDE-THE-SCRATCH-DIR")
    (scratch / "real.bin").write_bytes(b"REAL")
    (scratch / "link_to_secret").symlink_to(outside)
    (scratch / "dangling").symlink_to(scratch / "never_created")
    os.mkfifo(scratch / "pipe")
    (scratch / "nested").mkdir()
    (scratch / "nested" / "deep.bin").write_bytes(b"DEEP")
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
