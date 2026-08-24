import json
import os
import sys


def main():
    sys.stdin.read()
    document = {"status": "OK", "environ": sorted(os.environ), "argv": sys.argv[1:]}
    sys.stdout.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
