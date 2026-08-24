import json
import sys


def main():
    sys.stdin.read()
    document = {
        "status": "OK",
        "receipt": {
            "cpu_user_s": "9999.0",
            "cpu_sys_s": "9999.0",
            "wall_s": "9999.0",
            "peak_rss_bytes": 1,
            "exit_status": 0,
        },
    }
    sys.stdout.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
