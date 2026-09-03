import importlib.metadata
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

import blake3
import cypari2
from cysignals.alarm import AlarmInterrupt, alarm, cancel_alarm

from cairn import log

GP_BIN = "/opt/homebrew/bin/gp"
STACK_BYTES = 64_000_000
DEFAULT_STACK = "64M"
DEFAULT_TIMEOUT_S = 30.0
CALL_BOUND_S = 60.0


class GpMissing(RuntimeError):
    pass


class GpTimeout(RuntimeError):
    def __init__(self, pid, timeout_s):
        super().__init__(f"gp pid {pid} exceeded {timeout_s}s and was killed")
        self.pid = pid
        self.timeout_s = timeout_s


class PariBoundUnavailable(RuntimeError):
    pass


class PariStall(AlarmInterrupt):
    def __init__(self, name, bound_s, elapsed_s, *, earlier=None):
        self.name = name
        self.bound_s = bound_s
        self.elapsed_s = elapsed_s
        self.earlier = earlier
        super().__init__(self._text())

    def _text(self):
        if self.earlier is not None:
            return f"libpari refused: {self.name} after an earlier stall in this process ({self.earlier})"
        load = " ".join(f"{x:.1f}" for x in os.getloadavg())
        return (
            f"libpari stall: {self.name} passed the {self.bound_s:g} s in-process bound after "
            f"{self.elapsed_s:.1f} s (nbthreads {NBTHREADS}, load average {load}, "
            f"{threading.active_count()} Python threads); libpari is unusable in this process "
            "after an interrupted call"
        )


pari = cypari2.Pari()
pari.allocatemem(STACK_BYTES, silent=True)
NBTHREADS = int(pari("default(nbthreads)"))

_stall = None
_armed = False


def stalled():
    return _stall


def pari_versions():
    return {
        "libpari": ".".join(str(part) for part in pari.version()),
        "cypari2": importlib.metadata.version("cypari2"),
    }


def _alarm_owner():
    handler = signal.getsignal(signal.SIGALRM)
    return None if handler in (signal.SIG_DFL, None) else handler


def bounded(name, fn, *args, bound_s=None):
    global _stall, _armed
    if _stall is not None:
        raise PariStall(name, _stall.bound_s, 0.0, earlier=_stall)
    if _armed:
        raise PariBoundUnavailable(f"{name} was called inside another bounded call; one alarm serves one call")
    owner = _alarm_owner()
    if owner is not None:
        raise PariBoundUnavailable(
            f"SIGALRM is held by the Python handler {owner!r}; only cysignals' C handler interrupts a "
            f"libpari call, so {name} would run with no bound"
        )
    seconds = CALL_BOUND_S if bound_s is None else float(bound_s)
    start = time.monotonic()
    _armed = True
    alarm(seconds)
    try:
        return fn(*args)
    except AlarmInterrupt as interrupt:
        _stall = PariStall(name, seconds, time.monotonic() - start)
        raise _stall from interrupt
    finally:
        cancel_alarm()
        _armed = False


def ellcard(E, *, bound_s=None):
    return bounded("ellcard", pari.ellcard, E, bound_s=bound_s)


def ellsea(E, early_abort=0, *, bound_s=None):
    return bounded("ellsea", pari.ellsea, E, early_abort, bound_s=bound_s)


def ellorder(E, P, *, bound_s=None):
    return bounded("ellorder", pari.ellorder, E, P, bound_s=bound_s)


def gp_argv(stack=DEFAULT_STACK):
    return [GP_BIN, "-q", "-f", "-s", stack]


def _digest(text):
    return blake3.blake3(text.encode()).hexdigest()


def run_gp(args, stdin, *, timeout_s=DEFAULT_TIMEOUT_S, stack=DEFAULT_STACK):
    if not Path(GP_BIN).is_file():
        raise GpMissing(GP_BIN)
    argv = gp_argv(stack) + list(args)
    lg = log.get("gp")
    lg.debug("spawn", argv=argv, stdin_digest=_digest(stdin))
    start = time.monotonic()
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True
    )
    try:
        out, err = proc.communicate(stdin, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        lg.info("timeout", pid=proc.pid, timeout_s=timeout_s)
        raise GpTimeout(proc.pid, timeout_s) from None
    wall_ms = round((time.monotonic() - start) * 1000, 3)
    lg.info("exit", rc=proc.returncode, wall_ms=wall_ms)
    lg.debug("io", stdout_digest=_digest(out), stderr_digest=_digest(err))
    return proc.returncode, out, err
