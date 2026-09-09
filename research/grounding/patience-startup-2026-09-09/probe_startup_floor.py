"""The CPU a skill subprocess spends before any declared work begins.

    uv run python startup_probe.py [repeats]

Spawns the same interpreter runner.skill_argv would, with -c importing the skill
module rather than running it, and reads ru_utime + ru_stime from wait4 exactly as
runner.spawn_and_wait does. Reports the per-skill floor against the declared wall
each skill's cost profile names at its smallest declared size.
"""

import os
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
from cairn.skills import bsgs, instance_maker, rho_dp

SKILLS = {
    "instance_maker": ("cairn.skills.instance_maker", instance_maker),
    "bsgs": ("cairn.skills.bsgs", bsgs),
    "rho_dp": ("cairn.skills.rho_dp", rho_dp),
}
BARE = "sys"


def child_cpu_s(source):
    proc = subprocess.Popen(
        [sys.executable, "-c", f"import {source}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(Path("src").resolve().parent),
        env={**os.environ, "PYTHONPATH": str(Path("src").resolve())},
    )
    _, status, usage = os.wait4(proc.pid, 0)
    assert os.waitstatus_to_exitcode(status) == 0, source
    return usage.ru_utime + usage.ru_stime


def report(label, samples):
    print(
        f"{label:16} n={len(samples)} min={min(samples):.4f} median={statistics.median(samples):.4f} "
        f"max={max(samples):.4f}"
    )
    return statistics.median(samples)


repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 7
print(f"interpreter: {sys.executable}")
print()
bare = report("bare python", [child_cpu_s(BARE) for _ in range(repeats)])
print()
medians = {}
for name, (source, _profile_module) in SKILLS.items():
    medians[name] = report(name, [child_cpu_s(source) for _ in range(repeats)])
print()
print(f"{'skill':16} {'startup_s':>10} {'declared_wall_s':>16} {'size':>6} {'ceiling@4':>10} {'verdict':>10}")
for name, (_, module) in SKILLS.items():
    profile = module.COST_PROFILE
    smallest = min(profile.production.per_size)
    declared = profile.evaluate({"bits": smallest}).expected_wall_s
    ceiling = 4.0 * declared
    verdict = "BUSTS" if medians[name] > ceiling else "fits"
    print(f"{name:16} {medians[name]:10.4f} {declared:16.4f} {smallest:6d} {ceiling:10.4f} {verdict:>10}")
print()
print(f"spread across the three skills: {max(medians.values()) - min(medians.values()):.4f} s")
print(f"import cost above bare python:  {min(medians.values()) - bare:.4f} s to {max(medians.values()) - bare:.4f} s")
