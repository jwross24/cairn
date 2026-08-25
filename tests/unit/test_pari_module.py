import json
import logging
import os
import subprocess

import pytest

from cairn import cli, log, pari


def test_gp_argv_is_the_pinned_shape():
    assert pari.gp_argv("64M") == [pari.GP_BIN, "-q", "-f", "-s", "64M"]


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
    assert seen["args"][:5] == [pari.GP_BIN, "-q", "-f", "-s", "64M"]
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


REQUIRED_HEAD = {"bundle": ("show",), "attest": ("init",), "gate": ("selftest",), "justify": ("--statement", "0" * 64)}


@pytest.mark.parametrize("name", cli.registered())
def test_global_options_parse_before_or_after_subcommand(name):
    parser = cli.build_parser()
    head = list(REQUIRED_HEAD.get(name, ()))
    globals_argv = ["--db", "X", "--bundle", "B", "--pin", "P", "--attest", "A", "--log", "DEBUG"]
    before = parser.parse_args([*globals_argv, name, *head])
    after = parser.parse_args([name, *head, *globals_argv])
    picked = lambda ns: (ns.db, ns.bundle, ns.pin, ns.attest, ns.log)
    assert picked(before) == picked(after) == ("X", "B", "P", "A", "DEBUG")
    defaults = parser.parse_args([name, *head])
    assert picked(defaults) == tuple(cli.GLOBAL_DEFAULTS[k] for k in ("db", "bundle", "pin", "attest", "log"))


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
