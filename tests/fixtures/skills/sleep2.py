import sys
import time


def main():
    sys.stdin.read()
    time.sleep(2.0)
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
