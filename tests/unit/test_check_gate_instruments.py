import os
import re
import tomllib
from pathlib import Path

import _session_deadline
import pytest
from _session_deadline import (
    BACKSTOP_EXIT_CODE,
    BACKSTOP_GRACE,
    DEFAULT_SECONDS,
    SECONDS_VAR,
    SKIP_VAR,
    TIMEOUT_EXIT_CODE,
)

ROOT = Path(__file__).resolve().parent.parent.parent

CHECK_SH = (ROOT / "scripts" / "check.sh").read_text()
PYPROJECT = (ROOT / "pyproject.toml").read_text()


def joined_lines(text):
    return re.sub(r"\\\n\s*", " ", text).splitlines()


TESTS_GATE = next((line for line in joined_lines(CHECK_SH) if line.strip().startswith("gate tests ")), None)


@pytest.fixture
def restored_plugin_state():
    saved = _session_deadline.active_deadline()
    yield
    _session_deadline._active = saved


def test_the_tests_gate_exists_and_asks_for_a_durations_table():
    assert TESTS_GATE is not None, f"no 'gate tests ' line in check.sh:\n{CHECK_SH}"
    assert "--durations=25" in TESTS_GATE, TESTS_GATE


def test_the_tests_gate_logs_the_deadline_it_applied():
    assert 'say "DEADLINE ${CAIRN_SESSION_DEADLINE:-' in CHECK_SH
    assert 'say "DEADLINE bypassed: $CAIRN_SESSION_DEADLINE_SKIP"' in CHECK_SH


def test_the_logged_kill_codes_are_the_ones_the_two_instruments_exit_with():
    logged = re.search(r"the watchdog exits (\d+), its faulthandler backstop (\d+)s later exits (\d+)", CHECK_SH)
    assert logged is not None, CHECK_SH
    assert int(logged.group(1)) == TIMEOUT_EXIT_CODE
    assert int(logged.group(2)) == BACKSTOP_GRACE
    assert int(logged.group(3)) == BACKSTOP_EXIT_CODE


def test_the_logged_discriminator_is_the_banner_both_instruments_print():
    assert "'Timeout ('" in CHECK_SH, CHECK_SH


def test_the_bundled_faulthandler_plugin_is_blocked_for_this_session(pytestconfig):
    addopts = tomllib.loads(PYPROJECT)["tool"]["pytest"]["ini_options"]["addopts"]
    assert "-p no:faulthandler" in addopts, addopts
    assert pytestconfig.pluginmanager.is_blocked("faulthandler"), (
        "the bundled plugin is loaded and will cancel the backstop on the first reported failure"
    )


def test_the_logged_default_matches_the_deadline_pytest_actually_arms():
    logged = re.search(r"\$\{CAIRN_SESSION_DEADLINE:-(\d+)\}s", CHECK_SH)
    assert logged is not None, CHECK_SH
    assert int(logged.group(1)) == DEFAULT_SECONDS


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_an_absent_or_blank_setting_arms_the_logged_default(monkeypatch, restored_plugin_state, raw):
    monkeypatch.delenv(SKIP_VAR, raising=False)
    monkeypatch.delenv(SECONDS_VAR, raising=False)
    if raw is not None:
        monkeypatch.setenv(SECONDS_VAR, raw)

    _session_deadline.pytest_configure(None)
    try:
        armed = _session_deadline.active_deadline()
        assert armed is not None
        assert armed.seconds == float(DEFAULT_SECONDS)
        assert armed.thread.is_alive()
    finally:
        _session_deadline.pytest_unconfigure(None)


def test_teardown_stops_the_watchdog_and_releases_its_stderr_handle(monkeypatch, restored_plugin_state):
    monkeypatch.delenv(SKIP_VAR, raising=False)
    monkeypatch.setenv(SECONDS_VAR, "3600")

    _session_deadline.pytest_configure(None)
    armed = _session_deadline.active_deadline()
    assert armed is not None
    fd = armed.fd

    _session_deadline.pytest_unconfigure(None)

    assert not armed.thread.is_alive()
    assert _session_deadline.active_deadline() is None
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(fd)


def test_an_in_process_arm_leaves_the_session_backstop_with_its_owner(monkeypatch, restored_plugin_state):
    bypass = os.environ.get(SKIP_VAR, "").strip()
    session = _session_deadline.active_deadline()
    assert bypass or session is not None
    if session is None:
        return
    assert session.owns_backstop()

    monkeypatch.delenv(SKIP_VAR, raising=False)
    monkeypatch.setenv(SECONDS_VAR, "3600")
    _session_deadline.pytest_configure(None)
    nested = _session_deadline.active_deadline()
    try:
        assert nested is not session
        assert not nested.owns_backstop()
    finally:
        _session_deadline.pytest_unconfigure(None)

    assert session.owns_backstop()


def test_the_bypass_arms_nothing_at_all(monkeypatch, restored_plugin_state):
    monkeypatch.setenv(SKIP_VAR, "covering the bypass branch")
    monkeypatch.setenv(SECONDS_VAR, "1")
    _session_deadline._active = None

    _session_deadline.pytest_configure(None)

    assert _session_deadline.active_deadline() is None
