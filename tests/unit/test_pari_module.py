import json
import logging
import os
import signal
import subprocess
import sys
import time

import cysignals.signals
import pytest
from cysignals.alarm import AlarmInterrupt

from cairn import cli, log, pari

SMALL_CURVE = ([2, 3], 101)
# A finite loop of about 2.5 s here, so a dead alarm chain fails a test in seconds where an
# infinite loop would hang it past every watchdog; the child below may plant an infinite one.
FINITE_LOOP = "for(i=1,10^8,)"
POOL_WAIT = "parapply(x->while(1,),[1,2,3,4])"
CHILD_EXIT = 7
POOL_STALL_CHILD = f"""
import os, sys, time
from cairn import pari
real = pari.pari
class Stub:
    def ellcard(self, E):
        return real({POOL_WAIT!r})
pari.pari = Stub()
E = real.ellinit(*{SMALL_CURVE!r})
start = time.monotonic()
try:
    pari.ellcard(E, bound_s=1.0)
except pari.PariStall as stall:
    print(f"STALL {{time.monotonic() - start:.2f}} {{stall}}", flush=True)
    os._exit({CHILD_EXIT})
print("RETURNED", flush=True)
os._exit(1)
"""


class _StubbedLibpari:
    def __init__(self, real, expression):
        self.real = real
        self.expression = expression
        self.calls = []

    def ellcard(self, E):
        self.calls.append("ellcard")
        return self.real(self.expression)


class _Tripwire:
    def __init__(self):
        self.reached = []

    def _trip(self, name):
        self.reached.append(name)
        raise AssertionError(f"reached libpari: {name}")

    def ellcard(self, E):
        self._trip("ellcard")

    def ellsea(self, E, early_abort=0):
        self._trip("ellsea")

    def ellorder(self, E, P):
        self._trip("ellorder")


@pytest.fixture
def unpoisoned(monkeypatch):
    monkeypatch.setattr(pari, "_stall", None)


@pytest.mark.parametrize(("name", "args"), [("ellcard", ("E",)), ("ellsea", ("E",)), ("ellorder", ("E", "P"))])
def test_every_wrapper_refuses_after_an_earlier_stall_without_reaching_libpari(monkeypatch, unpoisoned, name, args):
    tripwire = _Tripwire()
    monkeypatch.setattr(pari, "pari", tripwire)
    monkeypatch.setattr(pari, "_stall", pari.PariStall("ellcard", 0.5, 0.5))
    with pytest.raises(pari.PariStall, match=f"libpari refused: {name} after an earlier stall"):
        getattr(pari, name)(*args)
    assert tripwire.reached == []


def test_a_bounded_call_inside_a_bounded_call_is_refused_and_the_outer_bound_still_clears(unpoisoned):
    E = pari.pari.ellinit(*SMALL_CURVE)
    n = int(pari.pari.ellcard(E))
    with pytest.raises(pari.PariBoundUnavailable, match="inside another bounded call"):
        pari.bounded("outer", lambda: pari.ellcard(E), bound_s=5)
    assert pari._armed is False
    assert int(pari.ellcard(E, bound_s=0.2)) == n


def test_nbthreads_is_pinned_to_one_in_process_and_in_every_gp_child():
    assert pari.NBTHREADS_PIN == 1
    assert pari.NBTHREADS == pari.NBTHREADS_PIN
    assert int(pari.pari("default(nbthreads)")) == pari.NBTHREADS_PIN
    assert pari.NUMERIC_PROFILE == "libpari nbthreads=1"
    rc, out, err = pari.run_gp([], "print(default(nbthreads))")
    assert (rc, out.strip(), err) == (0, str(pari.NBTHREADS_PIN), "")


def test_a_planted_busy_loop_raises_pari_stall_at_the_bound_and_poisons_the_wrappers(monkeypatch, unpoisoned):
    real = pari.pari
    E = real.ellinit(*SMALL_CURVE)
    n = int(real.ellcard(E))
    stub = _StubbedLibpari(real, FINITE_LOOP)
    monkeypatch.setattr(pari, "pari", stub)
    start = time.monotonic()
    with pytest.raises(pari.PariStall) as info:
        pari.ellcard(E, bound_s=0.5)
    elapsed = time.monotonic() - start
    stall = info.value
    assert 0.4 <= elapsed < 10
    assert isinstance(stall, KeyboardInterrupt)
    assert (stall.name, stall.bound_s, stall.earlier) == ("ellcard", 0.5, None)
    assert 0.4 <= stall.elapsed_s < 10
    assert str(stall).startswith("libpari stall: ellcard passed the 0.5 s in-process bound after ")
    assert f"nbthreads {pari.NBTHREADS}" in str(stall)
    assert pari.stalled() is stall
    with pytest.raises(pari.PariStall, match="libpari refused: ellcard after an earlier stall") as refused:
        pari.ellcard(E)
    assert refused.value.earlier is stall
    assert stub.calls == ["ellcard"]
    assert int(real.ellcard(E)) == n


def test_the_bound_is_cancelled_when_the_call_returns():
    E = pari.pari.ellinit(*SMALL_CURVE)
    n = int(pari.ellcard(E, bound_s=0.2))
    try:
        time.sleep(0.5)
    except AlarmInterrupt:
        pytest.fail("the alarm outlived the call it bounded")
    assert int(pari.ellcard(E)) == n
    assert pari.stalled() is None


def test_a_python_sigalrm_handler_refuses_the_call_rather_than_running_it_unbounded(monkeypatch, unpoisoned):
    real = pari.pari
    E = real.ellinit(*SMALL_CURVE)
    stub = _StubbedLibpari(real, FINITE_LOOP)
    monkeypatch.setattr(pari, "pari", stub)
    signal.signal(signal.SIGALRM, lambda *_: None)
    try:
        with pytest.raises(pari.PariBoundUnavailable, match="SIGALRM is held by the Python handler"):
            pari.ellcard(E, bound_s=0.3)
        assert stub.calls == []
    finally:
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        cysignals.signals.init_cysignals()
    assert pari._alarm_owner() is None
    with pytest.raises(pari.PariStall):
        pari.ellcard(E, bound_s=0.3)
    assert stub.calls == ["ellcard"]


def test_a_planted_thread_pool_wait_is_escaped_in_a_child_that_then_dies_loud():
    proc = subprocess.Popen(
        [sys.executable, "-c", POOL_STALL_CHILD],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        pytest.fail("the child did not escape the pool wait within 30 s")
    assert proc.returncode == CHILD_EXIT, (out, err)
    line = out.strip().splitlines()[-1]
    assert line.startswith("STALL ")
    assert float(line.split()[1]) < 10
    assert "libpari stall: ellcard passed the 1 s in-process bound after" in line


def test_gp_argv_is_the_pinned_shape():
    assert pari.gp_argv("64M") == [pari.GP_BIN, "-q", "-f", "-s", "64M", "-D", "nbthreads=1"]


def test_run_gp_spawns_the_pinned_argv_without_a_shell(monkeypatch):
    seen = {}
    real_popen = subprocess.Popen

    class Spy(real_popen):
        def __init__(self, args, *a, **kw):
            seen["args"] = list(args)
            seen["shell"] = kw.get("shell")
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", Spy)
    rc, out, err = pari.run_gp([], "print(1)")
    assert (rc, out.strip(), err) == (0, "1", "")
    assert seen["args"][:7] == [pari.GP_BIN, "-q", "-f", "-s", "64M", "-D", "nbthreads=1"]
    assert seen["shell"] is False


def test_run_gp_timeout_raises_and_leaves_no_zombie():
    with pytest.raises(pari.GpTimeout) as info:
        pari.run_gp([], "print(1)", timeout_s=0.001)
    with pytest.raises(ChildProcessError):
        os.waitpid(info.value.pid, os.WNOHANG)


def test_missing_gp_binary_raises_before_any_spawn(monkeypatch):
    spawned = []
    real_popen = subprocess.Popen

    class Spy(real_popen):
        def __init__(self, args, *a, **kw):
            spawned.append(list(args))
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", Spy)
    monkeypatch.setattr(pari, "GP_BIN", "/nonexistent/gp")
    with pytest.raises(pari.GpMissing):
        pari.run_gp([], "print(1)")
    assert spawned == []


REQUIRED_HEAD = {
    "bundle": ("show",),
    "attest": ("init",),
    "gate": ("selftest",),
    "ladder": ("plan",),
    "justify": ("--statement", "0" * 64),
}


def _picked(ns):
    return (ns.db, ns.bundle, ns.pin, ns.attest, ns.log)


@pytest.mark.parametrize("name", cli.registered())
def test_global_options_parse_before_or_after_subcommand(name):
    parser = cli.build_parser()
    head = list(REQUIRED_HEAD.get(name, ()))
    globals_argv = ["--db", "X", "--bundle", "B", "--pin", "P", "--attest", "A", "--log", "DEBUG"]
    before = parser.parse_args([*globals_argv, name, *head])
    after = parser.parse_args([name, *head, *globals_argv])
    assert _picked(before) == _picked(after) == ("X", "B", "P", "A", "DEBUG")
    defaults = parser.parse_args([name, *head])
    assert _picked(defaults) == tuple(cli.GLOBAL_DEFAULTS[k] for k in ("db", "bundle", "pin", "attest", "log"))


def test_log_records_are_json_parseable_and_digests_only_at_debug(caplog):
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    pari.run_gp([], "print(2)")
    info_records = [r for r in caplog.records if r.name == log.LOGGER_NAME]
    assert any(r.getMessage() == "exit" and r.fields["rc"] == 0 for r in info_records)
    assert all("stdin_digest" not in r.fields and "stdout_digest" not in r.fields for r in info_records)
    for record in info_records:
        json.loads(log.JsonFormatter().format(record))
    caplog.clear()
    caplog.set_level(logging.DEBUG, logger=log.LOGGER_NAME)
    pari.run_gp([], "print(2)")
    debug_records = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "io"]
    assert debug_records and "stdout_digest" in debug_records[0].fields
