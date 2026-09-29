import argparse
import contextlib
import ctypes
import ctypes.util
import errno
import hashlib
import itertools
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TICK_S = 0.005
THRESHOLD_S = 0.6
GRACE_S = 0.04
PROC_PIDT_SHORTBSDINFO = 13
SZOMB = 5
SSTOP = 4
MACH_SCALE = 1.0


class ScratchDir:
    def __init__(self, prefix):
        self.path = Path(tempfile.mkdtemp(prefix=prefix))

    def __enter__(self):
        return self.path

    def __exit__(self, kind, value, traceback):
        return False


def _load_proc():
    lib = ctypes.CDLL(ctypes.util.find_library("proc"), use_errno=True)
    lib.proc_listpgrppids.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
    lib.proc_listpgrppids.restype = ctypes.c_int
    lib.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    lib.proc_pid_rusage.restype = ctypes.c_int
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int
    return lib


def _timebase():
    class Info(ctypes.Structure):
        _fields_ = [("numerator", ctypes.c_uint32), ("denominator", ctypes.c_uint32)]

    info = Info()
    mach = ctypes.CDLL(ctypes.util.find_library("System"))
    mach.mach_timebase_info.argtypes = [ctypes.POINTER(Info)]
    mach.mach_timebase_info.restype = ctypes.c_int
    status = mach.mach_timebase_info(ctypes.byref(info))
    if status != 0 or info.denominator == 0:
        raise RuntimeError(f"mach_timebase_info status={status} numerator={info.numerator} denominator={info.denominator}")
    return info.numerator, info.denominator


def _mach_seconds(ticks, timebase):
    numerator, denominator = timebase
    return ticks * numerator / denominator / 1_000_000_000 * MACH_SCALE


def _write_json_atomically(path, value):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.partial")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(value))
        stream.flush()
        os.fsync(stream.fileno())
    Path(temporary).replace(path)


def _pid_cpu(lib, pid, timebase):
    buffer = (ctypes.c_uint64 * 32)()
    if lib.proc_pid_rusage(pid, 1, ctypes.byref(buffer)) != 0:
        return None
    return {
        "user_ticks": int(buffer[2]),
        "system_ticks": int(buffer[3]),
        "user_s": _mach_seconds(int(buffer[2]), timebase),
        "system_s": _mach_seconds(int(buffer[3]), timebase),
        "child_user_ticks": int(buffer[12]),
        "child_system_ticks": int(buffer[13]),
        "child_user_s": _mach_seconds(int(buffer[12]), timebase),
        "child_system_s": _mach_seconds(int(buffer[13]), timebase),
        "start_abstime": int(buffer[10]),
    }


def _pid_start_abstime(lib, pid):
    buffer = (ctypes.c_uint64 * 32)()
    if lib.proc_pid_rusage(pid, 1, ctypes.byref(buffer)) != 0:
        return None
    return int(buffer[10])


def _group_pids(lib, pgid, capacity=4096):
    buffer = (ctypes.c_uint32 * capacity)()
    count = lib.proc_listpgrppids(pgid, ctypes.byref(buffer), ctypes.sizeof(buffer))
    if count < 0:
        raise OSError(ctypes.get_errno(), "proc_listpgrppids")
    if count >= capacity:
        raise RuntimeError(f"process-group listing reached capacity {capacity}")
    return tuple(int(buffer[i]) for i in range(count))


def _signal_group_verified(lib, pgid, registry, sig):
    leader = next((item for item in _read_registry(registry) if int(item["pid"]) == pgid), None)
    if leader is None or _pid_start_abstime(lib, pgid) != leader["start_abstime"]:
        raise ProcessLookupError(f"process-group leader {pgid} identity changed")
    if pgid not in _group_pids(lib, pgid):
        raise ProcessLookupError(f"process-group leader {pgid} is absent from its group listing")
    os.killpg(pgid, sig)


def _pid_state(lib, pid):
    buffer = (ctypes.c_uint32 * 32)()
    ctypes.set_errno(0)
    size = lib.proc_pidinfo(pid, PROC_PIDT_SHORTBSDINFO, 0, ctypes.byref(buffer), ctypes.sizeof(buffer))
    error = ctypes.get_errno()
    if size <= 0:
        if error == errno.ESRCH:
            return None
        raise OSError(error or errno.EIO, f"proc_pidinfo returned {size} for pid {pid}")
    if size < 16:
        raise OSError(errno.EIO, f"proc_pidinfo returned short record size {size} for pid {pid}")
    if int(buffer[0]) != pid:
        raise OSError(errno.EIO, f"proc_pidinfo returned pid {int(buffer[0])} for requested pid {pid}")
    state = int(buffer[3])
    names = {1: "SIDL", 2: "SRUN", 3: "SSLEEP", 4: "SSTOP", 5: "SZOMB"}
    return {"pid": int(buffer[0]), "ppid": int(buffer[1]), "pgid": int(buffer[2]), "state": state, "state_name": names.get(state, "UNKNOWN")}


def _pid_query_error_refusal():
    class ErrorShim:
        def proc_pidinfo(self, _pid, _flavor, _arg, _buffer, _size):
            ctypes.set_errno(errno.EPERM)
            return 0

    try:
        _pid_state(ErrorShim(), os.getpid())
    except OSError as exc:
        return {"verdict": "REFUSE", "errno": exc.errno, "error": str(exc)}
    return {"verdict": "FAIL", "reason": "unexpected proc_pidinfo error was treated as a process state"}


def _sample(lib, pgid, timebase):
    start = time.monotonic()
    pids = _group_pids(lib, pgid)
    entries = []
    for pid in pids:
        usage = _pid_cpu(lib, pid, timebase)
        if usage is not None:
            entries.append({"pid": pid, **usage})
    return {"at_mono": time.monotonic(), "duration_s": time.monotonic() - start, "pids": pids, "entries": entries}


def _ledger_total(sample, ledger):
    for item in sample["entries"]:
        identity = (item["pid"], item["start_abstime"])
        own_s = item["user_s"] + item["system_s"]
        ledger[identity] = max(ledger.get(identity, 0.0), own_s)
    return sum(ledger.values())


def _append_pid(registry, pid, role):
    start_abstime = _pid_start_abstime(_load_proc(), pid)
    line = json.dumps({"pid": pid, "role": role, "start_abstime": start_abstime}, separators=(",", ":")).encode() + b"\n"
    fd = os.open(registry, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def _worker(role, registry, argument="0"):
    _append_pid(registry, os.getpid(), role)
    if role in ("root", "child"):
        next_role = "child" if role == "root" else "grandchild"
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "worker", next_role, registry, "1" if argument == "1" else "0"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=(argument == "1" and next_role == "grandchild"),
        )
        _append_pid(registry, process.pid, next_role)
        while True:
            pass
    if role == "sleeper":
        time.sleep(30)
        return 0
    if role == "calibration":
        report_dir = Path(argument)
        started = time.process_time()
        target = started + 0.12
        while time.process_time() < target:
            pass
        barrier = time.process_time()
        _write_json_atomically(report_dir / "barrier.json", {
            "started_process_time_s": started,
            "barrier_process_time_s": barrier,
            "process_time_delta_s": barrier - started,
        })
        sys.stdin.readline()
        finished = time.process_time()
        _write_json_atomically(report_dir / "finished.json", {"finished_process_time_s": finished})
        return 0
    if role == "short_burn":
        target = time.process_time() + 0.12
        while time.process_time() < target:
            pass
        return 0
    if role == "short_burn_barrier":
        result_dir = Path(argument)
        target = time.process_time() + 0.12
        while time.process_time() < target:
            pass
        _write_json_atomically(result_dir / "child-barrier.json", {"process_time_s": time.process_time()})
        while not (result_dir / "child-release").exists():
            time.sleep(0.001)
        return 0
    if role == "reap_parent":
        result_dir = Path(argument)
        for command in sys.stdin:
            if command.strip() == "exit":
                return 0
            if command.strip() not in ("gap", "sampled"):
                continue
            role = "short_burn" if command.strip() == "gap" else "short_burn_barrier"
            child = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "worker", role, registry, str(result_dir)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _, status, usage = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(status)
            own = _pid_cpu(_load_proc(), os.getpid(), _timebase())
            output_path = result_dir / f"{command.strip()}.json"
            _write_json_atomically(output_path, {
                "child_pid": child.pid,
                "child_exit_status": child.returncode,
                "child_wait4_user_s": usage.ru_utime,
                "child_wait4_system_s": usage.ru_stime,
                "child_wait4_cpu_s": usage.ru_utime + usage.ru_stime,
                "child_rusage_report": _pid_cpu(_load_proc(), child.pid, _timebase()),
                "parent_child_user_s": None if own is None else own["child_user_s"],
                "parent_child_system_s": None if own is None else own["child_system_s"],
                "parent_child_cpu_s": None if own is None else own["child_user_s"] + own["child_system_s"],
            })
    while True:
        pass


def _read_registry(path):
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    unique = {}
    for record in records:
        unique[int(record["pid"])] = record
    return list(unique.values())


def _cleanup(lib, leader, registry, timeout_s=2.0):
    pids = _read_registry(registry)
    leader_record = next((item for item in pids if int(item["pid"]) == leader), None)
    group_error = None
    if (
        leader_record is not None
        and _pid_start_abstime(lib, leader) == leader_record["start_abstime"]
        and leader in _group_pids(lib, leader)
    ):
        try:
            os.killpg(leader, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            group_error = str(exc)
    for item in pids:
        pid = int(item["pid"])
        if _pid_start_abstime(lib, pid) != item["start_abstime"]:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            pass
    deadline = time.monotonic() + timeout_s
    states = {}
    leader_reaped = False
    while time.monotonic() < deadline:
        try:
            waited, _ = os.waitpid(leader, os.WNOHANG)
            leader_reaped = waited == leader
        except ChildProcessError:
            leader_reaped = True
        states = {}
        for item in pids:
            pid = int(item["pid"])
            state = _pid_state(lib, pid)
            if state is None:
                states[pid] = {"identity": "absent", "state": None}
            elif _pid_start_abstime(lib, pid) == item["start_abstime"]:
                states[pid] = {"identity": "same_process", "state": state}
            else:
                states[pid] = {"identity": "identity_mismatch", "state": state}
        if leader_reaped and all(
            value["identity"] == "absent"
            or (value["identity"] == "same_process" and value["state"]["state"] == SZOMB)
            for value in states.values()
        ):
            break
        time.sleep(0.01)
    return {
        "created": pids,
        "group_kill_error": group_error,
        "leader_reaped": leader_reaped,
        "states_after_cleanup": {str(pid): state for pid, state in states.items()},
        "all_not_running": all(
            value["identity"] == "absent"
            or (value["identity"] == "same_process" and value["state"]["state"] == SZOMB)
            for value in states.values()
        ),
    }


def _start_worker(role, registry, escaped=False):
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "worker", role, str(registry), "1" if escaped else "0"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if len(_read_registry(registry)) >= (3 if role == "root" else 1):
            break
        time.sleep(0.005)
    return proc


def _live_run(lib, timebase, escaped=False, disable_enforcement=False):
    with ScratchDir("cairn-cpu-live-") as temp:
        registry = Path(temp) / "pids.jsonl"
        proc = _start_worker("root", registry, escaped=escaped)
        result = {"case": "escaped_session" if escaped else "live_tree_cpu_stop", "pgid": proc.pid, "threshold_s": THRESHOLD_S, "scratch_directory": str(temp)}
        exit_code = 1
        try:
            time.sleep(0.03)
            before = _sample(lib, proc.pid, timebase)
            result["initial_sample"] = before
            ledger = {}
            triggered = None
            samples = []
            deadline = time.monotonic() + 4.0
            initial_total = _ledger_total(before, ledger)
            samples.append({"total_s": initial_total, **before})
            if initial_total >= THRESHOLD_S:
                triggered = {"sample_total_s": initial_total, "sample": before, "trigger_mono": time.monotonic()}
            while triggered is None and time.monotonic() < deadline:
                sample = _sample(lib, proc.pid, timebase)
                total = _ledger_total(sample, ledger)
                samples.append({"total_s": total, **sample})
                if total >= THRESHOLD_S:
                    triggered = {"sample_total_s": total, "sample": sample, "trigger_mono": time.monotonic()}
                    break
                time.sleep(TICK_S)
            result["samples"] = samples
            if disable_enforcement:
                result["observer_saw_cpu_threshold"] = triggered is not None
            if triggered is None:
                result["verdict"] = "FAIL"
                result["reason"] = "sampled CPU threshold did not fire before four-second probe bound"
            else:
                result["trigger"] = triggered
                requested_stop = time.monotonic()
                signal_error = None
                if not disable_enforcement:
                    try:
                        _signal_group_verified(lib, proc.pid, registry, signal.SIGSTOP)
                    except OSError as exc:
                        signal_error = f"{type(exc).__name__}: {exc}"
                result["enforcement_signal"] = None if disable_enforcement else "SIGSTOP"
                result["enforcement_signal_error"] = signal_error
                result["stop_request_delay_s"] = requested_stop - triggered["trigger_mono"]
                stable_deadline = time.monotonic() + 0.5
                stopped_sample = None
                stopped_states = {}
                expected_group_count = 2 if escaped else 3
                while time.monotonic() < stable_deadline:
                    stopped_sample = _sample(lib, proc.pid, timebase)
                    stopped_states = {pid: _pid_state(lib, pid) for pid in stopped_sample["pids"]}
                    if len(stopped_sample["pids"]) == expected_group_count and all(
                        state is not None and state["state"] == SSTOP for state in stopped_states.values()
                    ):
                        break
                    time.sleep(0.005)
                final_ledger = dict(ledger)
                stopped_total = _ledger_total(stopped_sample, final_ledger)
                stopped_ok = len(stopped_sample["pids"]) == expected_group_count and all(
                    state is not None and state["state"] == SSTOP for state in stopped_states.values()
                )
                result["stopped_sample"] = stopped_sample
                result["stopped_states"] = stopped_states
                result["stop_observed"] = stopped_ok
                result["stopped_self_cpu_s"] = stopped_total
                result["observed_overrun_s"] = stopped_total - THRESHOLD_S
                result["tick_s"] = TICK_S
                result["max_sample_duration_s"] = max((item["duration_s"] for item in samples), default=0.0)
                result["max_observed_sample_interval_s"] = max(
                    (current["at_mono"] - previous["at_mono"] for previous, current in itertools.pairwise(samples)),
                    default=0.0,
                )
                result["stop_to_stable_sample_s"] = stopped_sample["at_mono"] - requested_stop
                if escaped:
                    escaped_pid = next((int(item["pid"]) for item in _read_registry(registry) if item["role"] == "grandchild"), None)
                    result["escaped_grandchild_at_group_stop"] = {
                        "pid": escaped_pid,
                        "group_member": escaped_pid in stopped_sample["pids"] if escaped_pid is not None else None,
                        "state": _pid_state(lib, escaped_pid) if escaped_pid is not None else None,
                        "self_cpu": _pid_cpu(lib, escaped_pid, timebase) if escaped_pid is not None else None,
                    }
                if disable_enforcement:
                    result["verdict"] = "REFUSE" if triggered is not None and not stopped_ok else "FAIL"
                    result["reason"] = "CPU threshold was observed with a live workload but no stop signal was sent"
                    exit_code = 2 if result["verdict"] == "REFUSE" else 1
                elif escaped:
                    escaped_state = result["escaped_grandchild_at_group_stop"]["state"]
                    limitation_observed = stopped_ok and escaped_state is not None and escaped_state["state"] == 2
                    result["verdict"] = "COUNTEREXAMPLE" if limitation_observed else "FAIL"
                    result["reason"] = "escaped session remained runnable while every sampled process-group member stopped"
                    exit_code = 0 if limitation_observed else 1
                else:
                    result["verdict"] = "PASS" if stopped_ok and signal_error is None else "FAIL"
                    exit_code = 0 if result["verdict"] == "PASS" else 1
        finally:
            cleanup = _cleanup(lib, proc.pid, registry)
            result["cleanup"] = cleanup
        if not cleanup["all_not_running"] or not cleanup["leader_reaped"]:
            result["verdict"] = "FAIL"
            result["reason"] = "cleanup left a created process running"
            exit_code = 1
        return result, exit_code


def _wall_run(lib):
    with ScratchDir("cairn-wall-") as temp:
        registry = Path(temp) / "pids.jsonl"
        proc = _start_worker("sleeper", registry)
        wall_cap_s = 0.12
        started = time.monotonic()
        timed_out = False
        waited_usage = None
        result = {"case": "wall_timeout", "wall_cap_s": wall_cap_s, "scratch_directory": str(temp)}
        exit_code = 1
        try:
            while True:
                waited_pid, waited_status, waited_usage = os.wait4(proc.pid, os.WNOHANG)
                if waited_pid == proc.pid:
                    proc.returncode = os.waitstatus_to_exitcode(waited_status)
                    break
                elapsed = time.monotonic() - started
                if elapsed >= wall_cap_s:
                    timed_out = True
                    _signal_group_verified(lib, proc.pid, registry, signal.SIGTERM)
                    break
                time.sleep(min(TICK_S, wall_cap_s - elapsed))
            if timed_out:
                grace_deadline = time.monotonic() + GRACE_S
                while time.monotonic() < grace_deadline:
                    waited_pid, waited_status, waited_usage = os.wait4(proc.pid, os.WNOHANG)
                    if waited_pid == proc.pid:
                        proc.returncode = os.waitstatus_to_exitcode(waited_status)
                        break
                    time.sleep(0.005)
                else:
                    _signal_group_verified(lib, proc.pid, registry, signal.SIGKILL)
                if proc.returncode is None:
                    _, status, waited_usage = os.wait4(proc.pid, 0)
                    proc.returncode = os.waitstatus_to_exitcode(status)
            waited = time.monotonic() - started
            result.update({
                "wall_s": waited,
                "exit_status": proc.returncode,
                "timed_out": timed_out,
                "cpu_user_s": None if waited_usage is None else waited_usage.ru_utime,
                "cpu_system_s": None if waited_usage is None else waited_usage.ru_stime,
                "verdict": "PASS" if timed_out else "FAIL",
            })
            exit_code = 0 if timed_out else 1
        finally:
            cleanup = _cleanup(lib, proc.pid, registry)
            result["cleanup"] = cleanup
        if not cleanup["all_not_running"] or not cleanup["leader_reaped"]:
            result["verdict"] = "FAIL"
            result["reason"] = "cleanup left a created process running or the direct child unreaped"
            exit_code = 1
        return result, exit_code


def _metadata():
    git = shutil.which("git")
    try:
        if git is None:
            raise FileNotFoundError("git")
        head = subprocess.run([git, "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
    runner_path = ROOT / "src/cairn/runner.py"
    return {
        "source_head": head,
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(runner_path.read_bytes()).hexdigest() if runner_path.exists() else None,
        "os": platform.platform(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "python": sys.version,
    }


def _clock_and_population(lib, timebase):
    parent = os.getpid()
    before = _sample(lib, os.getpgrp(), timebase)
    own = _pid_cpu(lib, parent, timebase)
    member_states = {pid: _pid_state(lib, pid) for pid in before["pids"]}
    return {
        "pgid": os.getpgrp(),
        "listed_population": before["pids"],
        "listed_population_count": len(before["pids"]),
        "member_states": member_states,
        "all_reported_pgids_match": all(state is not None and state["pgid"] == os.getpgrp() for state in member_states.values()),
        "self_pid_present": parent in before["pids"],
        "sample_duration_s": before["duration_s"],
        "self_usage": own,
        "timebase_numer": timebase[0],
        "timebase_denom": timebase[1],
        "units_conversion": "seconds = Mach absolute ticks * numerator / denominator / 1e9",
    }


def _clock_calibration(lib, timebase):
    with ScratchDir("cairn-clock-") as temp:
        registry = Path(temp) / "pids.jsonl"
        barrier_path = Path(temp) / "barrier.json"
        finished_path = Path(temp) / "finished.json"
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "worker", "calibration", str(registry), str(temp)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        sample = None
        wait_usage = None
        status = None
        try:
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and not barrier_path.exists():
                time.sleep(TICK_S)
            if barrier_path.exists():
                sample = _sample(lib, proc.pid, timebase)
                proc.stdin.write(b"exit\n")
                proc.stdin.flush()
            while time.monotonic() < deadline:
                waited_pid, status, wait_usage = os.wait4(proc.pid, os.WNOHANG)
                if waited_pid == proc.pid:
                    proc.returncode = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(TICK_S)
            if proc.returncode is None:
                os.killpg(proc.pid, signal.SIGKILL)
                _, status, wait_usage = os.wait4(proc.pid, 0)
                proc.returncode = os.waitstatus_to_exitcode(status)
            barrier = json.loads(barrier_path.read_text()) if barrier_path.exists() else None
            finished = json.loads(finished_path.read_text()) if finished_path.exists() else None
            live = next((item for item in sample["entries"] if item["pid"] == proc.pid), None) if sample is not None else None
            wait_cpu_s = None if wait_usage is None else wait_usage.ru_utime + wait_usage.ru_stime
            result = {
                "target_process_cpu_s": 0.12,
                "proc_pid_rusage_live_at_barrier": live,
                "barrier_process_time": barrier,
                "worker_process_time_after_release": finished,
                "wait4_cpu_s": wait_cpu_s,
                "live_sample_vs_process_time_s": None if live is None or barrier is None else live["user_s"] + live["system_s"] - barrier["barrier_process_time_s"],
                "wait4_vs_process_time_s": None if wait_cpu_s is None or finished is None else wait_cpu_s - finished["finished_process_time_s"],
                "exit_status": proc.returncode,
            }
        finally:
            with contextlib.suppress(BrokenPipeError, OSError):
                proc.stdin.close()
            cleanup = _cleanup(lib, proc.pid, registry)
            result["cleanup"] = cleanup
        result["verdict"] = "PASS" if (
            result["exit_status"] == 0
            and result["live_sample_vs_process_time_s"] is not None
            and abs(result["live_sample_vs_process_time_s"]) < 0.025
            and cleanup["all_not_running"]
            and cleanup["leader_reaped"]
        ) else "REFUSE"
        return result


def _reaped_counter_probe(lib, timebase):
    with ScratchDir("cairn-reaped-") as temp:
        registry = Path(temp) / "pids.jsonl"
        gap_path = Path(temp) / "gap.json"
        barrier_path = Path(temp) / "child-barrier.json"
        release_path = Path(temp) / "child-release"
        sampled_path = Path(temp) / "sampled.json"
        control = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "worker", "reap_parent", str(registry), str(temp)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        result = {"scratch_directory": str(temp)}
        try:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and len(_read_registry(registry)) < 1:
                time.sleep(0.005)
            before_gap = _sample(lib, control.pid, timebase)
            control.stdin.write(b"gap\n")
            control.stdin.flush()
            deadline = time.monotonic() + 4.0
            while time.monotonic() < deadline and not gap_path.exists():
                time.sleep(0.005)
            after_gap = _sample(lib, control.pid, timebase)
            gap_result = json.loads(gap_path.read_text()) if gap_path.exists() else None
            gap_pid = None if gap_result is None else int(gap_result["child_pid"])
            result["between_snapshots"] = {
                "sample_before": before_gap,
                "sample_after": after_gap,
                "sample_gap_s": after_gap["at_mono"] - before_gap["at_mono"],
                "child_result": gap_result,
                "child_absent_from_both_snapshots": gap_pid is not None and gap_pid not in before_gap["pids"] and gap_pid not in after_gap["pids"],
                "parent_reaped_counters_after_child_exit": None if not after_gap["entries"] else {
                    "child_user_s": after_gap["entries"][0]["child_user_s"],
                    "child_system_s": after_gap["entries"][0]["child_system_s"],
                },
            }
            before_sampled = _sample(lib, control.pid, timebase)
            before_parent_usage = next(item for item in before_sampled["entries"] if item["pid"] == control.pid)
            control.stdin.write(b"sampled\n")
            control.stdin.flush()
            live_samples = []
            sampled_pid = None
            deadline = time.monotonic() + 4.0
            while time.monotonic() < deadline and not barrier_path.exists():
                records = _read_registry(registry)
                sampled_pid = next((int(item["pid"]) for item in records if item["role"] == "short_burn_barrier"), sampled_pid)
                sample = _sample(lib, control.pid, timebase)
                if sampled_pid in sample["pids"]:
                    live_samples.extend(item for item in sample["entries"] if item["pid"] == sampled_pid)
                time.sleep(TICK_S)
            barrier = json.loads(barrier_path.read_text()) if barrier_path.exists() else None
            if barrier is not None:
                barrier_sample = _sample(lib, control.pid, timebase)
                live_samples.extend(item for item in barrier_sample["entries"] if item["pid"] == sampled_pid)
                release_path.touch()
            else:
                barrier_sample = _sample(lib, control.pid, timebase)
            deadline = time.monotonic() + 4.0
            while time.monotonic() < deadline and not sampled_path.exists():
                time.sleep(0.005)
            after_sampled = _sample(lib, control.pid, timebase)
            sampled_result = json.loads(sampled_path.read_text()) if sampled_path.exists() else None
            after_parent_usage = next((item for item in after_sampled["entries"] if item["pid"] == control.pid), None)
            last_child_sample = live_samples[-1] if live_samples else None
            sampled_child_cpu = None if last_child_sample is None else last_child_sample["user_s"] + last_child_sample["system_s"]
            reaped_delta_cpu = None if after_parent_usage is None else (
                after_parent_usage["child_user_s"] - before_parent_usage["child_user_s"]
                + after_parent_usage["child_system_s"] - before_parent_usage["child_system_s"]
            )
            wait4_child_cpu = None if sampled_result is None else sampled_result["child_wait4_cpu_s"]
            naive_sum = None if sampled_child_cpu is None or reaped_delta_cpu is None else sampled_child_cpu + reaped_delta_cpu
            result["sampled_then_reaped"] = {
                "sample_before": before_sampled,
                "barrier": barrier,
                "child_live_sample_count": len(live_samples),
                "child_self_cpu_at_last_live_sample_s": sampled_child_cpu,
                "sample_after_reap": after_sampled,
                "child_result": sampled_result,
                "child_absent_after_reap": sampled_pid is not None and sampled_pid not in after_sampled["pids"],
                "parent_reaped_counter_delta_cpu_s": reaped_delta_cpu,
                "naive_self_plus_reaped_sum_s": naive_sum,
                "naive_sum_excess_over_child_wait4_s": None if naive_sum is None or wait4_child_cpu is None else naive_sum - wait4_child_cpu,
                "counter_sum_is_diagnostic_not_accounting": True,
            }
        finally:
            release_path.touch(exist_ok=True)
            with contextlib.suppress(BrokenPipeError, OSError):
                control.stdin.write(b"exit\n")
                control.stdin.flush()
            with contextlib.suppress(subprocess.TimeoutExpired):
                control.wait(timeout=1.0)
            result["cleanup"] = _cleanup(lib, control.pid, registry)
        return result


def _runner_receipts():
    from cairn import keys, runner, substrate
    from cairn.profile import Evaluation
    from cairn.skills import toy_curve

    fixtures = ROOT / "tests/fixtures"
    identity = toy_curve.identity_bundle()
    tool_digests = identity["tool_digests"]
    recipe = {
        "skill_identity_hash": keys.identity_bundle_hash(identity),
        "inputs": {},
        "seed": 1,
        "tool_versions": {"cypari2": tool_digests["cypari2"]},
        "container_digest": identity["container_digest"],
        "salt": "",
    }
    records = []
    with ScratchDir("cairn-receipt-") as temp:
        base = Path(temp)
        with substrate.Substrate.open(base / "substrate.sqlite") as sub:
            cases = [
                ("post_exit_overage", "skills.cpu_burner", Evaluation(0.0125, 0.0125, 0.0), 100.0, 30.0, {"FIXTURE_GRANDCHILD": "1"}),
                ("wall_timeout", "skills.sleep2", Evaluation(0.0125, 0.0125, 0.0), 1.0, 0.0, {}),
            ]
            for name, module, evaluation, wall_mult, wall_floor, extra in cases:
                attempt = runner.launch(
                    sub,
                    module,
                    recipe | {"seed": len(records) + 1},
                    bundle_hash="cd" * 32,
                    evaluation=evaluation,
                    ceiling_multiplier=4,
                    tool_digests=tool_digests,
                    scratch_root=base / "runs",
                    wall_cap_multiplier=wall_mult,
                    wall_cap_floor_s=wall_floor,
                    subprocess_startup_ms=0,
                    env_extra={"PYTHONPATH": str(fixtures), **extra},
                    do_not_cache=True,
                )
                receipt = sub.get_receipt(attempt.receipt_hash)
                records.append({"case": name, "status": attempt.status, "receipt": dict(receipt) if receipt else None})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("all", "worker", "live", "calibrate", "pid-query-error"))
    parser.add_argument("role", nargs="?")
    parser.add_argument("registry", nargs="?")
    parser.add_argument("escaped", nargs="?", default="0")
    parser.add_argument("--disable-enforcement", action="store_true")
    parser.add_argument("--misconvert-clock", action="store_true")
    args = parser.parse_args()
    if sys.platform != "darwin":
        print(json.dumps({"verdict": "REFUSE", "reason": "probe requires macOS libproc and Mach time"}, sort_keys=True))
        return 2
    if args.mode == "worker":
        return _worker(args.role, args.registry, args.escaped)
    if args.mode == "pid-query-error":
        result = {"metadata": _metadata(), "pid_query_error": _pid_query_error_refusal()}
        print(json.dumps(result, sort_keys=True))
        return 2 if result["pid_query_error"]["verdict"] == "REFUSE" else 1
    global MACH_SCALE
    if args.misconvert_clock:
        MACH_SCALE = 10.0
    lib = _load_proc()
    timebase = _timebase()
    if args.mode == "live":
        result, code = _live_run(lib, timebase, disable_enforcement=args.disable_enforcement)
        result["metadata"] = _metadata()
        print(json.dumps(result, sort_keys=True))
        return code
    if args.mode == "calibrate":
        result = {"metadata": _metadata(), "clock_calibration": _clock_calibration(lib, timebase)}
        print(json.dumps(result, sort_keys=True))
        return 0 if result["clock_calibration"]["verdict"] == "PASS" else 2
    outputs = {
        "metadata": _metadata(),
        "clock_population": _clock_and_population(lib, timebase),
        "clock_calibration": _clock_calibration(lib, timebase),
        "reaped_counter_probe": _reaped_counter_probe(lib, timebase),
    }
    outputs["live_tree"], live_code = _live_run(lib, timebase)
    outputs["escaped_session"], escaped_code = _live_run(lib, timebase, escaped=True)
    outputs["wall_timeout"], wall_code = _wall_run(lib)
    outputs["current_runner"] = _runner_receipts()
    receipt_statuses = {item["case"]: item["status"] for item in outputs["current_runner"]}
    calibration = outputs["clock_calibration"]
    reaped = outputs["reaped_counter_probe"]
    outputs["arm_results"] = {
        "same_group_live_cpu_stop": outputs["live_tree"]["verdict"],
        "escaped_session_boundary": outputs["escaped_session"]["verdict"],
        "wall_timeout_control": outputs["wall_timeout"]["verdict"],
        "clock_calibration": calibration["verdict"],
        "short_lived_child_snapshot_gap": "OBSERVED" if (
            reaped["between_snapshots"]["child_absent_from_both_snapshots"]
            and reaped["between_snapshots"]["parent_reaped_counters_after_child_exit"]
        ) else "FAIL",
        "sampled_then_reaped_double_count": "OBSERVED" if (
            reaped["sampled_then_reaped"]["child_live_sample_count"] > 0
            and reaped["sampled_then_reaped"]["naive_sum_excess_over_child_wait4_s"] > 0
            and reaped["sampled_then_reaped"]["child_absent_after_reap"]
        ) else "FAIL",
        "runner_post_exit_overage": receipt_statuses.get("post_exit_overage"),
        "runner_wall_timeout": receipt_statuses.get("wall_timeout"),
    }
    outputs["scope_statement"] = "Bounded observations cover the listed cases; a sampled process group does not prove complete process-tree containment."
    print(json.dumps(outputs, sort_keys=True))
    receipt_code = 0 if receipt_statuses == {"post_exit_overage": "BUDGET_EXCEEDED", "wall_timeout": "BLOCKED"} else 1
    calibration_code = 0 if outputs["arm_results"]["clock_calibration"] == "PASS" else 1
    reaped_code = 0 if (
        outputs["arm_results"]["short_lived_child_snapshot_gap"] == "OBSERVED"
        and outputs["arm_results"]["sampled_then_reaped_double_count"] == "OBSERVED"
        and outputs["reaped_counter_probe"]["cleanup"]["all_not_running"]
        and outputs["reaped_counter_probe"]["cleanup"]["leader_reaped"]
    ) else 1
    return max(live_code, escaped_code, wall_code, receipt_code, calibration_code, reaped_code)


if __name__ == "__main__":
    sys.exit(main())
