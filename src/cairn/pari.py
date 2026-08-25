import importlib.metadata
import os
import subprocess
import time

import blake3
import cypari2

from cairn import log

GP_BIN = "/opt/homebrew/bin/gp"
STACK_BYTES = 64_000_000
DEFAULT_STACK = "64M"
DEFAULT_TIMEOUT_S = 30.0


class GpMissing(RuntimeError):
    pass


class GpTimeout(RuntimeError):
    def __init__(self, pid, timeout_s):
        super().__init__(f"gp pid {pid} exceeded {timeout_s}s and was killed")
        self.pid = pid
        self.timeout_s = timeout_s


pari = cypari2.Pari()
pari.allocatemem(STACK_BYTES, silent=True)


def pari_versions():
    return {
        "libpari": ".".join(str(part) for part in pari.version()),
        "cypari2": importlib.metadata.version("cypari2"),
    }


def ellcard(E):
    return pari.ellcard(E)


def ellsea(E, early_abort=0):
    return pari.ellsea(E, early_abort)


def ellorder(E, P):
    return pari.ellorder(E, P)


def gp_argv(stack=DEFAULT_STACK):
    return [GP_BIN, "-q", "-f", "-s", stack]


def _digest(text):
    return blake3.blake3(text.encode()).hexdigest()


def run_gp(args, stdin, *, timeout_s=DEFAULT_TIMEOUT_S, stack=DEFAULT_STACK):
    if not os.path.isfile(GP_BIN):
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
