import sys

CHUNK = "e" * 1024


def main():
    sys.stdin.read()
    for _ in range(1024):
        sys.stderr.write(CHUNK)
    sys.stderr.flush()
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
