"""Probe: what os.wait4 reports for a skill's descendants under three shapes.

Arms: a child that reaps its CPU-burning grandchild, a child that orphans it, and a
child killed at the wall cap before it can reap. Prints one JSON row per arm.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cairn import runner

BURN = "x = 0\nfor i in range(40_000_000): x += i\n"
GROW = "b = bytearray(48 * 1024 * 1024)\nb[::4096] = b'\\x01' * (len(b) // 4096)\n"

CHILD = """
import subprocess, sys, time
mode = sys.argv[1]
g = subprocess.Popen([sys.executable, "-c", {body!r}])
if mode == "reap":
    g.wait()
elif mode == "killed":
    time.sleep(600)
sys.stdout.write('{{"status":"OK"}}\\n')
"""


def arm(mode, body, wall_cap_s):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        err = Path(tmp) / "err"
        launch = runner.spawn_and_wait(
            [sys.executable, "-c", CHILD.format(body=body), mode],
            out,
            err,
            wall_cap_s=wall_cap_s,
            env=dict(os.environ),
        )
        return {
            "arm": mode,
            "cpu_user_s": round(launch.cpu_user_s, 3),
            "cpu_sys_s": round(launch.cpu_sys_s, 3),
            "wall_s": round(launch.wall_s, 3),
            "peak_rss_mb": round(launch.peak_rss_bytes / 2**20, 1),
            "timed_out": launch.timed_out,
            "exit_status": launch.exit_status,
        }


def main():
    rows = []
    for body, label in ((BURN, "cpu"), (GROW, "rss")):
        for mode, cap in (("reap", 600.0), ("orphan", 600.0), ("killed", 3.0)):
            row = arm(mode, body, cap)
            row["burns"] = label
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n") if len(sys.argv) > 1 else None
    return 0


if __name__ == "__main__":
    sys.exit(main())
