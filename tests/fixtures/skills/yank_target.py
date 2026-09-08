import json
import os
import signal
import sys
import time
from pathlib import Path


def main():
    document = json.load(sys.stdin)
    scratch = Path(sys.argv[1])

    def finish(_signum=None, _frame=None):
        (scratch / "sigterm_seen").write_text("term")
        print('{"status":"OK"}', flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal.SIG_IGN if document.get("ignore_term") else finish)
    (scratch / "ready").write_text(str(os.getpid()))
    if document.get("finish"):
        print('{"status":"OK"}', flush=True)
        return
    deadline = time.monotonic() + 30
    while not (scratch / "finish").exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("harness did not finish the child")
        time.sleep(0.01)
    print('{"status":"OK"}', flush=True)


if __name__ == "__main__":
    main()
