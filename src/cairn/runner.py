import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from cairn import canon, keys, log
from cairn.substrate import blob_hash

LOG_STEP = "runner"
SCRUB_PREFIX = "CAIRN_DB"
HARNESS_ONLY_KEYS = ("receipt",)
SKILL_STATUSES = ("OK", "FAIL", "DISAGREE")
STATUS_OK = "OK"
STATUS_FAIL = "FAIL"
STATUS_DISAGREE = "DISAGREE"
STATUS_BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
STATUS_SKILL_YANKED = "SKILL_YANKED"
STATUS_INTERRUPTED = "INTERRUPTED"
HARNESS_TERMINATED = (STATUS_BUDGET_EXCEEDED, STATUS_SKILL_YANKED, STATUS_INTERRUPTED)
ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TZ")
MAXRSS_UNIT_BYTES = ("darwin",)
MAXRSS_UNIT_KB = ("linux", "freebsd", "openbsd", "netbsd", "sunos")
TICK_S = 0.005
GRACE_S = 0.25
UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class ParsedOutput:
    well_formed: bool
    status: str = None
    reason: str = None
    document: dict = field(default_factory=dict)

    @classmethod
    def of(cls, document, status):
        return cls(True, status, None, document)

    @classmethod
    def malformed(cls, reason):
        return cls(False, None, reason, {})


def _decoded(stdout_bytes):
    if isinstance(stdout_bytes, str):
        return stdout_bytes
    if stdout_bytes.startswith(UTF8_BOM):
        raise ValueError("stdout starts with a UTF-8 BOM")
    return stdout_bytes.decode("utf-8")


def _reject_constant(token):
    raise ValueError(f"stdout carries the non-JSON constant {token}")


def parse_skill_output(stdout_bytes):
    try:
        text = _decoded(stdout_bytes)
    except (UnicodeDecodeError, ValueError) as exc:
        return ParsedOutput.malformed(str(exc))
    if not text.strip():
        return ParsedOutput.malformed("stdout is empty")
    try:
        document, end = json.JSONDecoder(parse_constant=_reject_constant).raw_decode(
            text
        )
    except RecursionError:
        return ParsedOutput.malformed("stdout nests deeper than the decoder allows")
    except (ValueError, TypeError) as exc:
        return ParsedOutput.malformed(f"stdout is not one JSON document: {exc}")
    if text[end:].strip():
        return ParsedOutput.malformed(
            "stdout carries trailing bytes after the document"
        )
    if not isinstance(document, dict):
        return ParsedOutput.malformed(
            f"stdout is not a JSON object, got {type(document).__name__}"
        )
    status = document.get("status")
    if status not in SKILL_STATUSES:
        return ParsedOutput.malformed(
            f"status must be one of {SKILL_STATUSES}, got {status!r}"
        )
    return ParsedOutput.of(
        {k: v for k, v in document.items() if k not in HARNESS_ONLY_KEYS}, status
    )


def status_for(parsed, exit_status, wall_s, ceiling_s):
    if ceiling_s is not None and wall_s > ceiling_s:
        return STATUS_BUDGET_EXCEEDED
    if exit_status != 0:
        return STATUS_FAIL
    if not parsed.well_formed:
        return STATUS_FAIL
    if parsed.status == STATUS_DISAGREE:
        return STATUS_DISAGREE
    if parsed.status == STATUS_OK:
        return STATUS_OK
    return STATUS_FAIL


def ceiling_for(declared_expectation_s, ceiling_multiplier):
    return float(ceiling_multiplier) * float(declared_expectation_s)


def child_env(extra=None, base=None):
    source = os.environ if base is None else base
    env = {k: v for k, v in source.items() if k in ENV_ALLOWLIST}
    for key, value in dict(extra or {}).items():
        if key.startswith(SCRUB_PREFIX):
            raise ValueError(f"{key} would hand the child a substrate path")
        env[key] = value
    return env


def maxrss_bytes(ru_maxrss, platform=None):
    plat = sys.platform if platform is None else platform
    if plat in MAXRSS_UNIT_BYTES:
        return int(ru_maxrss)
    if plat.startswith(MAXRSS_UNIT_KB):
        return int(ru_maxrss) * 1024
    raise NotImplementedError(f"ru_maxrss units are unknown for {plat!r}")


def tool_digests_hash(tool_digests):
    return keys.node_hash(
        "tool_digests",
        canon.encode(canon.Map(canon.STR, canon.STR), dict(tool_digests)),
    )


def _lg():
    return log.get(LOG_STEP)


def skill_argv(module, scratch_dir):
    return [sys.executable, "-m", str(module), str(scratch_dir)]


def allocated_bytes(root):
    total = 0
    for dirpath, _, filenames in os.walk(root, followlinks=False):
        total += os.lstat(dirpath).st_blocks * 512
        for name in filenames:
            total += os.lstat(os.path.join(dirpath, name)).st_blocks * 512
    return total


def _signal_group(pgid, pid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError, PermissionError:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


@dataclass(frozen=True)
class Launch:
    exit_status: int
    start_mono: float
    end_mono: float
    wall_s: float
    cpu_user_s: float
    cpu_sys_s: float
    peak_rss_bytes: int
    timed_out: bool
    argv: tuple


def spawn_and_wait(
    argv,
    out_path,
    err_path,
    *,
    ceiling_s,
    env,
    stdin_bytes=b"",
    tick=TICK_S,
    grace=GRACE_S,
):
    lg = log.get(LOG_STEP)
    lg.debug("spawn", argv=list(argv), stdin_digest=blob_hash(stdin_bytes))
    stdin_path = Path(out_path).with_name("stdin")
    Path(stdin_path).write_bytes(stdin_bytes)
    handle_out = open(out_path, "wb", buffering=0)
    handle_err = open(err_path, "wb", buffering=0)
    handle_in = open(stdin_path, "rb")
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
        reaped = False
        timed_out = False
        terminated_at = None
        status = 0
        usage = None
        try:
            while True:
                pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
                if pid == proc.pid:
                    reaped = True
                    break
                elapsed = time.monotonic() - start
                if ceiling_s is not None and not timed_out and elapsed >= ceiling_s:
                    timed_out = True
                    terminated_at = elapsed
                    _signal_group(pgid, proc.pid, signal.SIGTERM)
                elif timed_out and elapsed >= terminated_at + grace:
                    _signal_group(pgid, proc.pid, signal.SIGKILL)
                remaining = (
                    tick
                    if ceiling_s is None
                    else min(tick, max(0.0, ceiling_s - elapsed))
                )
                time.sleep(remaining or tick)
        finally:
            if not reaped:
                _signal_group(pgid, proc.pid, signal.SIGKILL)
                _, status, usage = os.wait4(proc.pid, 0)
        _signal_group(pgid, proc.pid, signal.SIGKILL)
        end = time.monotonic()
        proc.returncode = os.waitstatus_to_exitcode(status)
    finally:
        handle_out.close()
        handle_err.close()
        handle_in.close()
    launch = Launch(
        exit_status=proc.returncode,
        start_mono=start,
        end_mono=end,
        wall_s=end - start,
        cpu_user_s=usage.ru_utime,
        cpu_sys_s=usage.ru_stime,
        peak_rss_bytes=maxrss_bytes(usage.ru_maxrss),
        timed_out=timed_out,
        argv=tuple(argv),
    )
    lg.info(
        "exit",
        rc=launch.exit_status,
        wall_ms=round(launch.wall_s * 1000, 3),
        cpu_s=round(launch.cpu_user_s + launch.cpu_sys_s, 6),
        rss=launch.peak_rss_bytes,
        timed_out=timed_out,
    )
    return launch
