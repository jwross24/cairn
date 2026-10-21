import os
import subprocess
import sys
import time

import pytest

from cairn import procwalk, runner

LEADER = 100


def _watch(rows):
    return procwalk.EscapeWatch(LEADER, LEADER, lambda _leader: {pid: (ppid, pgid, 0) for pid, ppid, pgid in rows})


@pytest.mark.parametrize(
    ("rows", "escaped"),
    [
        ([(LEADER, 1, LEADER)], False),
        ([(LEADER, 1, LEADER), (101, LEADER, LEADER), (102, 101, LEADER)], False),
        ([(LEADER, 1, LEADER), (101, LEADER, 101)], True),
        ([(LEADER, 1, LEADER), (101, LEADER, LEADER), (102, 101, 102)], True),
        ([(LEADER, 1, LEADER), (200, 1, 200)], False),
        ([(LEADER, 1, LEADER), (101, 1, 101)], False),
    ],
)
def test_the_walk_names_only_descendants_outside_the_leaders_group(rows, escaped):
    assert _watch(rows).tick() is escaped


def test_an_escape_seen_once_stays_seen_after_the_descendant_is_gone():
    rows = [(LEADER, 1, LEADER), (101, LEADER, 101)]
    watch = procwalk.EscapeWatch(LEADER, LEADER, lambda _leader: {pid: (ppid, pgid, 0) for pid, ppid, pgid in rows})
    assert watch.tick()
    rows.clear()
    assert watch.tick()
    assert watch.escaped == {(101, 0)}


def test_without_a_process_table_nothing_is_reported():
    assert procwalk.EscapeWatch(LEADER, LEADER, None).tick() is False


def test_the_real_process_table_lists_this_process_with_its_parent_and_group():
    table = runner._PROCESS_TABLE
    assert table is not None
    ppid, pgid, _ = table(os.getpid())[os.getpid()]
    assert ppid == os.getppid()
    assert pgid == os.getpgrp()


def test_the_real_process_table_reaches_a_grandchild_in_another_group():
    code = (
        "import subprocess, sys; "
        "subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'], start_new_session=True)"
    )
    child = subprocess.Popen([sys.executable, "-c", code])
    try:
        deadline = time.monotonic() + 15
        watch = procwalk.EscapeWatch(child.pid, child.pid, runner._PROCESS_TABLE)
        while not watch.tick():
            assert time.monotonic() < deadline
            time.sleep(0.02)
        assert {pid for pid, _ in watch.escaped}
    finally:
        child.kill()
        child.wait()


@pytest.mark.parametrize(
    ("escaped", "scope"),
    [(False, runner.SCOPE_TREE), (True, runner.SCOPE_TRUNCATED)],
)
def test_an_escaped_descendant_is_a_truncated_scope_and_only_then(escaped, scope):
    got = runner.measurement_scope(
        sampled_extra=False, survivors=frozenset(), killed=False, sampled=True, escaped=escaped
    )
    assert got == scope
    assert runner.scope_is_verified_complete(got) is (not escaped)
