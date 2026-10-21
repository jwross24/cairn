import os
import signal
import subprocess
import time
from pathlib import Path

from cairn import log, procwalk, runner
from cairn.substrate import blob_hash


def spawn_and_wait(argv, out_path, err_path, *, wall_cap_s, env, stdin_bytes, tick, grace, is_yanked):
    lg = log.get(runner.LOG_STEP)
    lg.debug("spawn", argv=list(argv), stdin_digest=blob_hash(stdin_bytes))
    stdin_path = Path(out_path).with_name("stdin")
    Path(stdin_path).write_bytes(stdin_bytes)
    handle_out = Path(out_path).open("wb", buffering=0)
    handle_err = Path(err_path).open("wb", buffering=0)
    handle_in = stdin_path.open("rb")
    try:
        start = time.monotonic()
        proc = subprocess.Popen(
            list(argv),
            stdin=handle_in,
            stdout=handle_out,
            stderr=handle_err,
            env=env,
            start_new_session=True,
            close_fds=True,
        )
        pgid = proc.pid
        lister = runner._PGRP_LISTER
        sampled = lister is not None
        watch = procwalk.EscapeWatch(proc.pid, pgid, runner._PROCESS_TABLE)
        sampled_extra = False
        survivors = frozenset()
        reaped = False
        terminated_at = None
        timed_out = False
        skill_yanked = False
        status = 0
        usage = None
        try:
            while True:
                pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
                if pid == proc.pid:
                    reaped = True
                    break
                if sampled and not sampled_extra:
                    sampled_extra = bool(lister(pgid) - {proc.pid})
                if sampled:
                    watch.tick()
                if is_yanked is not None and is_yanked():
                    skill_yanked = True
                elapsed = time.monotonic() - start
                if terminated_at is None and (skill_yanked or (wall_cap_s is not None and elapsed >= wall_cap_s)):
                    terminated_at = elapsed
                    timed_out = not skill_yanked
                    runner._signal_group(pgid, proc.pid, signal.SIGTERM)
                elif terminated_at is not None and elapsed >= terminated_at + grace:
                    runner._signal_group(pgid, proc.pid, signal.SIGKILL)
                remaining = tick if wall_cap_s is None else min(tick, max(0.0, wall_cap_s - elapsed))
                time.sleep(remaining or tick)
        finally:
            if not reaped:
                runner._signal_group(pgid, proc.pid, signal.SIGKILL)
                _, status, usage = os.wait4(proc.pid, 0)
        if sampled:
            survivors = lister(pgid) - {proc.pid}
            sampled_extra = sampled_extra or bool(survivors)
        runner._signal_group(pgid, proc.pid, signal.SIGKILL)
        end = time.monotonic()
        proc.returncode = os.waitstatus_to_exitcode(status)
    finally:
        handle_out.close()
        handle_err.close()
        handle_in.close()
    launch = runner.Launch(
        exit_status=proc.returncode,
        start_mono=start,
        end_mono=end,
        wall_s=end - start,
        cpu_user_s=usage.ru_utime,
        cpu_sys_s=usage.ru_stime,
        peak_rss_bytes=runner.maxrss_bytes(usage.ru_maxrss),
        timed_out=timed_out,
        skill_yanked=skill_yanked,
        argv=tuple(argv),
        measurement_scope=runner.measurement_scope(
            sampled_extra=sampled_extra,
            survivors=survivors,
            killed=terminated_at is not None,
            sampled=sampled,
            escaped=bool(watch.escaped),
        ),
    )
    lg.info(
        "exit",
        rc=launch.exit_status,
        wall_ms=round(launch.wall_s * 1000, 3),
        cpu_s=round(launch.cpu_user_s + launch.cpu_sys_s, 6),
        rss=launch.peak_rss_bytes,
        timed_out=timed_out,
        skill_yanked=skill_yanked,
    )
    if terminated_at is not None:
        lg.warning(
            "kill",
            wall_cap_s=wall_cap_s,
            terminated_at_s=round(terminated_at, 6),
            wall_s=round(launch.wall_s, 6),
            rc=launch.exit_status,
        )
    return launch
