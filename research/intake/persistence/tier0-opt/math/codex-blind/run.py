import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from independent import branch_keep, depth1_count, level12_origin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TIER0 = ROOT / "tier0"
ZONE = ZoneInfo("America/New_York")
STATE = Path("/private/tmp/cairn-long-calibration/overnight-state.json")
INPUTS = ("runall_final.jsonl", "trees_c.jsonl", "trees_mac.jsonl")


def calibration_deadline():
    now = time.time()
    local = datetime.fromtimestamp(now, ZONE)
    stop = local.replace(hour=1, minute=45, second=0, microsecond=0)
    resume = local.replace(hour=5, minute=30, second=0, microsecond=0)
    if stop.timestamp() <= now < resume.timestamp():
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        stamp = state.get("timestamp")
        if isinstance(stamp, str):
            stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise RuntimeError("calibration timestamp lacks a time zone")
            stamp = stamp.timestamp()
        threshold = local.replace(hour=2, minute=0, second=0, microsecond=0).timestamp()
        if state.get("paused") is not False or not isinstance(stamp, (float, int)) or not threshold < stamp <= now:
            raise RuntimeError("calibration quiet window is active")
        return resume.timestamp()
    if now >= resume.timestamp():
        stop += timedelta(days=1)
    return stop.timestamp() - 5


def check_nice():
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 10:
        raise RuntimeError(f"niceness is {priority}; required >= 10")
    return priority


def clock_check():
    output = subprocess.check_output(["date", "+%s %Y-%m-%d %H:%M:%S %Z"], text=True).strip()
    print(json.dumps({"clock": output, "nice": check_nice()}), flush=True)
    if int(output.split()[0]) >= calibration_deadline():
        raise RuntimeError("calibration cutoff reached")


def emit(path, record):
    with path.open("a") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True), flush=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def branch(out):
    from export_cfg import export, _static
    from tier0v2 import multisets

    summary = Counter()
    st = _static(12)
    pdata, solver = st["pd"], st["fl"]
    for vertex in (14336, 28672):
        for digits in sorted(multisets(vertex), key=lambda m: (len(m), m)):
            clock_check()
            tag = f"{vertex}-" + "".join(map(str, digits))
            cfg = out / f"{tag}.cfg"
            export(digits, str(cfg))
            files = []
            for flag in (False, True):
                clock_check()
                dest = out / f"{tag}-{'bs' if flag else 'plain'}.txt"
                err = dest.with_suffix(".stderr")
                command = [str(TIER0 / "lvl12"), str(cfg), "0", "12"]
                if flag:
                    command.append("bs")
                started = time.monotonic()
                with dest.open("w") as stream, err.open("w") as errors:
                    subprocess.run(command, stdout=stream, stderr=errors, check=True)
                emit(out / "events.jsonl", {"command": command, "seconds": time.monotonic() - started})
                files.append(dest)
            baseline, actual = (read_kernel(p, len(digits)) for p in files)
            if not set(actual) <= set(baseline):
                for key in sorted(set(actual) - set(baseline)):
                    emit(out / "disagreements.jsonl", {"part": "A", "vertex": vertex, "digits": digits, "pattern": key, "issue": "bs-only output"})
                    summary["disagreements"] += 1
            row = Counter()
            for key, (kind, origin, raw) in baseline.items():
                a, nu, eps = key
                independently_solved = level12_origin(digits, nu, eps, a, pdata, solver)
                if independently_solved is None:
                    raise AssertionError(("kernel output has no independent lattice solution", raw))
                co = solver.U2
                det = co[0][0] * co[1][1] - co[0][1] * co[1][0]
                delta = (origin[0] - independently_solved[0], origin[1] - independently_solved[1])
                assert (delta[0] * co[1][1] - delta[1] * co[1][0]) % det == 0
                assert (co[0][0] * delta[1] - co[0][1] * delta[0]) % det == 0
                expected = kind == "EXACT" or branch_keep(digits, nu, eps, independently_solved, co)
                observed = key in actual
                row["tested"] += 1
                row["exact_passthrough" if kind == "EXACT" else "open_tested"] += 1
                row["independent_keep" if expected else "independent_drop"] += 1
                row["agreement" if expected == observed else "disagreement"] += 1
                if expected != observed or observed and actual[key][2] != raw:
                    emit(out / "disagreements.jsonl", {"part": "A", "vertex": vertex, "digits": digits, "pattern": key, "independent_keep": expected, "kernel_keep": observed, "plain": raw, "bs": actual.get(key)})
                    summary["disagreements"] += 1
            summary.update(row)
            emit(out / "branch.jsonl", {"vertex": vertex, "digits": digits, **row})
    emit(out / "summary.jsonl", {"part": "A", **summary})


def read_kernel(path, q):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] not in ("OPEN", "EXACT"):
            raise ValueError(line)
        a, nu = map(int, fields[1:3])
        eps = tuple(map(int, fields[3:3 + q]))
        key = (a, nu, eps)
        if key in result:
            raise ValueError(("duplicate output pattern", key))
        result[key] = (fields[0], tuple(map(int, fields[3 + q:5 + q])), line)
    return result


def records(path):
    for line_number, line in enumerate(path.open(), 1):
        r = json.loads(line)
        for eq in r.get("eqs", []):
            if not isinstance(eq, dict):
                continue
            for e in eq.get("exceptional", []):
                if len(e) == 3:
                    a, y, sol = e
                    yield line_number, (r["s"], tuple(eq["M"]), a, None, None, y, sol)
                else:
                    yield line_number, (r["s"], tuple(eq["M"]), e[1], e[2], tuple(e[3]), e[4][0], e[4][1])
        for m, a, nu, eps, (y, sol) in r.get("exceptional", []):
            yield line_number, (r["s"], tuple(m), a, nu, tuple(eps), y, sol)


def h2(out, limit, maxcases):
    import deepcut
    from lattice import Coset

    clock_check()
    lam = deepcut.kernel_lattice()
    emit(out / "lattice.jsonl", {"u1": lam.u1, "u2": lam.u2})
    queues = [(iter(records(TIER0 / name)), name) for name in INPUTS]
    seen = set()
    totals = Counter()
    anchors = {}
    while queues and totals["patterns_sampled"] < limit:
        active = []
        for queue, name in queues:
            item = next(queue, None)
            if item is None:
                continue
            active.append((queue, name))
            line_number, record = item
            s, digits, a, nu, eps, y, sol = record
            key = (s, digits, a, nu, eps, y)
            if key in seen:
                totals["duplicate_records"] += 1
                continue
            seen.add(key)
            if not isinstance(y, int):
                totals["noninteger_anchor_excluded"] += 1
                continue
            factors = factor237(y)
            if factors is None or factors[0] != a:
                raise ValueError(record)
            clock_check()
            reps = deepcut.all_representations(digits, y)
            if nu is not None:
                reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
            if not reps:
                raise ValueError(("no representation", record))
            co = Coset(factors[1:], lam.u1, lam.u2)
            anchors[y] = factors
            pcounts = Counter()
            for rep_index, rep in enumerate(reps):
                clock_check()
                count = depth1_count(a, y, rep[1])
                verdict, bound, cases, stats = deepcut.deep_cut(co, a, rep, 1, maxcases)
                pcounts["representations_sampled"] += 1
                detail = {"source": name, "line": line_number, "record": record, "rep_index": rep_index, "rep": rep, "independent_count": count, "oracle_closed": verdict, "oracle_cases": cases, "oracle_stats": stats}
                if verdict is None:
                    pcounts["oracle_budget_excluded"] += 1
                else:
                    pcounts["compared"] += 1
                    agrees = (count == 0) == verdict
                    counts_agree = count == stats[0]
                    pcounts["verdict_agreement" if agrees else "verdict_disagreement"] += 1
                    pcounts["count_agreement" if counts_agree else "count_disagreement"] += 1
                    if not agrees or not counts_agree:
                        emit(out / "disagreements.jsonl", {"part": "B", **detail})
                emit(out / "h2-representations.jsonl", detail)
            totals["patterns_sampled"] += 1
            totals.update(pcounts)
            emit(out / "h2-patterns.jsonl", {"source": name, "line": line_number, "record": record, **pcounts})
            if totals["patterns_sampled"] >= limit:
                break
        queues = active
    emit(out / "summary.jsonl", {"part": "B", **totals})
    plants(out, lam, anchors)


def factor237(value):
    if value <= 0:
        return None
    factors = []
    for prime in (2, 3, 7):
        exponent = 0
        while value % prime == 0:
            value //= prime
            exponent += 1
        factors.append(exponent)
    return tuple(factors) if value == 1 else None


def plants(out, lam, anchors):
    from descent import cut_coset
    from lattice import Coset

    vectors = []
    for i, j in itertools.product(range(-32, 33), repeat=2):
        x = i * lam.u1[0] + j * lam.u2[0]
        z = i * lam.u1[1] + j * lam.u2[1]
        if x > 0 and z > 0:
            vectors.append((x + z, x, z, i, j))
    _, xstep, zstep, i, j = min(vectors)
    modulus = 10 ** 96
    ratio = pow(3, xstep, modulus) * pow(7, zstep, modulus) % modulus
    totals = Counter()
    for y, (a, b, c) in list(anchors.items())[:8]:
        clock_check()
        residue = y % modulus
        co = Coset((b, c), lam.u1, lam.u2)
        for t in range(1, 1_000_001):
            residue = residue * ratio % modulus
            text = str(residue).zfill(96)
            if "0" in text:
                continue
            x, z = t * xstep, t * zstep
            assert lam.contains(x, z)
            de = [(int(d), e) for e, d in enumerate(reversed(text)) if d != "1"]
            count = depth1_count(a, y, de)
            accepted = cut_coset(co, a, residue, 96)
            survives = count > 0 and accepted is not None and accepted.contains(b + x, c + z)
            emit(out / "plants.jsonl", {"anchor": y, "x": x, "z": z, "lattice_coefficients": [t * i, t * j], "tail": residue, "independent_count": count, "cut_survives": accepted is not None, "point_contained": accepted is not None and accepted.contains(b + x, c + z), "survives": survives, "full_deepcut_enumeration": False})
            totals["survived" if survives else "false_kill"] += 1
            break
        else:
            totals["anchor_search_exhausted"] += 1
    emit(out / "summary.jsonl", {"part": "plants", **totals})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=("all", "branch", "h2"), default="all")
    parser.add_argument("--patterns", type=int, default=300)
    parser.add_argument("--maxcases", type=int, default=200_000)
    parser.add_argument("--seconds", type=int, default=3600)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    clock_check()
    os.chdir(TIER0)
    sys.path.insert(0, str(TIER0))
    if args.worker:
        out = args.worker
        sources = [HERE / "independent.py", HERE / "run.py", TIER0 / "lvl12", TIER0 / "deepcut.py", *(TIER0 / name for name in INPUTS)]
        emit(out / "events.jsonl", {"started_epoch": time.time(), "hashes": {str(p): digest(p) for p in sources}, "args": vars(args) | {"worker": str(out)}})
        if args.part in ("all", "branch"):
            branch(out)
        if args.part in ("all", "h2"):
            h2(out, args.patterns, args.maxcases)
        assert all(digest(p) == json.loads((out / "events.jsonl").read_text().splitlines()[0])["hashes"][str(p)] for p in sources)
        emit(out / "events.jsonl", {"completed_epoch": time.time()})
        return
    out = HERE / datetime.now(ZONE).strftime("run-%Y%m%d-%H%M%S-%f")
    out.mkdir()
    deadline = min(time.time() + args.seconds, calibration_deadline())
    command = [sys.executable, "-B", str(HERE / "run.py"), "--part", args.part, "--patterns", str(args.patterns), "--maxcases", str(args.maxcases), "--worker", str(out)]
    env = os.environ | {key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "PYTHONDONTWRITEBYTECODE")}
    with (out / "console.log").open("w") as console:
        process = subprocess.Popen(command, env=env, stdout=console, stderr=subprocess.STDOUT, start_new_session=True)
        print(f"Output: {out}", flush=True)
        while process.poll() is None:
            if time.time() >= deadline:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                emit(out / "events.jsonl", {"stopped_epoch": time.time(), "reason": "time budget or calibration cutoff"})
                raise SystemExit(124)
            time.sleep(0.5)
    print(f"Exit: {process.returncode}", flush=True)
    raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()
