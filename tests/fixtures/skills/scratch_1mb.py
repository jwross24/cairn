import sys
from pathlib import Path


def main():
    sys.stdin.read()
    scratch = Path(sys.argv[1])
    (scratch / "payload.bin").write_bytes(b"s" * (1024 * 1024))
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
