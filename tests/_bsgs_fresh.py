import json
import math
import multiprocessing
import os
import sys

from cairn.skills import bsgs, instance_maker


def recover(job):
    bits, seed = job
    inst = instance_maker.run(bits, 1000 + seed)
    out = bsgs.run(bits, seed, inst.p, inst.a, inst.b, inst.n, inst.P, inst.Q)
    return {
        "seed": seed,
        "recovered": out.x == inst.x,
        "status": out.status,
        "cross_check": out.cross_check["result"],
        "entries": out.memory["entries"],
        "entries_expected": math.isqrt(inst.n - 1),
    }


def main():
    bits, count = json.loads(sys.stdin.read())
    jobs = [(bits, seed) for seed in range(1, count + 1)]
    with multiprocessing.get_context("spawn").Pool(min(count, os.process_cpu_count() or 1)) as pool:
        rows = pool.map(recover, jobs, chunksize=1)
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
