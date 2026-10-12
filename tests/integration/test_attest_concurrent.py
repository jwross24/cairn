import fcntl
import json
import multiprocessing
import os
import stat
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from cairn import attest, claims, cli, exits, substrate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories


def _append_worker(path, body, barrier, results, index, unlocked):
    original_open = Path.open

    class CoordinatedFile:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            self.file.__enter__()
            barrier.wait(timeout=10)
            return self

        def __exit__(self, *args):
            return self.file.__exit__(*args)

        def tell(self):
            offset = self.file.tell()
            if unlocked:
                barrier.wait(timeout=10)
            return offset

        def __getattr__(self, name):
            return getattr(self.file, name)

    def opened(self, *args, **kwargs):
        file = original_open(self, *args, **kwargs)
        return CoordinatedFile(file) if self == path else file

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "open", opened)
        if unlocked:
            patch.setattr(attest.fcntl, "flock", lambda *args: None)
        offset = attest.append_record(path, body)
    results.put((index, offset))


def _concurrent_appends(path, bodies, *, unlocked=False):
    context = multiprocessing.get_context("spawn")
    barrier, results = context.Barrier(2), context.Queue()
    children = [
        context.Process(target=_append_worker, args=(path, body, barrier, results, index, unlocked))
        for index, body in enumerate(bodies)
    ]
    try:
        for child in children:
            child.start()
        for child in children:
            child.join(timeout=20)
            assert child.exitcode == 0, child.exitcode
        return dict(results.get(timeout=2) for _ in children)
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(timeout=5)
            child.close()
        results.close()
        results.join_thread()


def _reviews():
    statements = [factories.claim_statement(seed=seed) for seed in (1, 2)]
    verdicts = [factories.review_verdict(statement.hash, seed=index) for index, statement in enumerate(statements)]
    verdicts = [replace(verdict, reviewer=verdict.reviewer + "x" * 65536) for verdict in verdicts]
    return statements, verdicts, [claims.review_verdict_canonical(verdict) for verdict in verdicts]


def _visible_mirrors(tmp_path, path, statements, verdicts, offsets):
    with substrate.Substrate.open(tmp_path / "store.sqlite") as sub:
        for index, statement in enumerate(statements):
            claims.write_claim_statement(sub, statement)
            claims.write_review_verdict(sub, replace(verdicts[index], file_offset=offsets[index]))
        return [claims.visible_review_verdicts(sub, statement.hash, path) for statement in statements]


def _assert_own_offsets(path, bodies, verdicts, offsets):
    assert len(set(offsets.values())) == 2, offsets
    for index, body in enumerate(bodies):
        assert attest.read_record(path, offsets[index]) == body
        assert attest.attestation_record_matches(path, offsets[index], verdicts[index].record_digest)


def _exit_with_lock(path, acquired):
    with path.open("ab") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        acquired.set()
        os._exit(17)


def test_process_exit_releases_the_append_lock(tmp_path):
    path = tmp_path / "attestations.log"
    path.touch()
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    child = context.Process(target=_exit_with_lock, args=(path, acquired))
    try:
        child.start()
        assert acquired.wait(timeout=10)
        child.join(timeout=10)
        assert child.exitcode == 17
    finally:
        if child.is_alive():
            child.terminate()
            child.join(timeout=5)
        child.close()
    with path.open("ab") as contender:
        fcntl.flock(contender.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(contender.fileno(), fcntl.LOCK_UN)
    statements, verdicts, bodies = _reviews()
    offsets = _concurrent_appends(path, bodies)
    _assert_own_offsets(path, bodies, verdicts, offsets)
    assert all(_visible_mirrors(tmp_path, path, statements, verdicts, offsets))


@pytest.mark.parametrize("append_only", [False, True], ids=["ordinary", "deployment"])
def test_concurrent_appends_bind_each_complete_frame_and_visible_mirror(tmp_path, clear_flags, append_only):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    path.touch()
    prefix = b"existing record"
    assert attest.append_record(path, prefix) == 0
    if append_only:
        protected = attest._set_append_only(path)
        if hasattr(os, "chflags"):
            assert protected
            assert path.stat().st_flags & stat.UF_APPEND
        else:
            assert not protected
    statements, verdicts, bodies = _reviews()
    offsets = _concurrent_appends(path, bodies)
    actual = list(attest.records(path))
    assert len(actual) == 3
    assert actual[0] == (0, prefix)
    assert {body for _, body in actual[1:]} == set(bodies)
    _assert_own_offsets(path, bodies, verdicts, offsets)
    visible = _visible_mirrors(tmp_path, path, statements, verdicts, offsets)
    assert [[row["record_digest"] for row in rows] for rows in visible] == [
        [verdict.record_digest] for verdict in verdicts
    ]


def test_unlocked_eof_collision_leaves_one_mirror_invisible(tmp_path):
    path = tmp_path / "attestations.log"
    path.touch()
    statements, verdicts, bodies = _reviews()
    offsets = _concurrent_appends(path, bodies, unlocked=True)
    actual = list(attest.records(path))
    assert len(actual) == 2
    assert {body for _, body in actual} == set(bodies)
    assert offsets == {0: 0, 1: 0}
    with pytest.raises(AssertionError):
        _assert_own_offsets(path, bodies, verdicts, offsets)
    assert sum(len(rows) for rows in _visible_mirrors(tmp_path, path, statements, verdicts, offsets)) == 1


@pytest.mark.parametrize("failure", ["lock", "write", "flush"])
def test_append_failure_reports_error_without_success_or_mirror(tmp_path, pinned_bundle, monkeypatch, capsys, failure):
    bundle_path, pin_path = pinned_bundle()
    path = tmp_path / "attestations.log"
    path.touch()
    statement = factories.claim_statement(seed=1)
    verdict = factories.review_verdict(statement.hash, seed=1)
    database = tmp_path / "store.sqlite"
    with substrate.Substrate.open(database) as sub:
        claims.write_claim_statement(sub, statement)
    record = tmp_path / "review.json"
    record.write_text(json.dumps({name: getattr(verdict, name) for name in attest.VERDICT_RECORD_FIELDS}))
    message = f"injected {failure} failure"
    original_open = Path.open

    class FailedFile:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.file.__exit__(*args)

        def __getattr__(self, name):
            if name == failure:
                return refused
            return getattr(self.file, name)

    def refused(*args):
        raise OSError(message)

    def opened(self, *args, **kwargs):
        file = original_open(self, *args, **kwargs)
        return FailedFile(file) if self == path else file

    with monkeypatch.context() as fault:
        if failure == "lock":
            fault.setattr(attest.fcntl, "flock", refused)
        else:
            fault.setattr(Path, "open", opened)
        code = cli.main(
            [
                "--db",
                str(database),
                "--bundle",
                str(bundle_path),
                "--pin",
                str(pin_path),
                "--attest",
                str(path),
                "attest",
                "append",
                "--kind",
                "review_verdict",
                "--record",
                str(record),
                "--json",
            ]
        )
    output = capsys.readouterr()
    assert code == exits.BACKEND
    assert output.out == ""
    assert message in output.err
    with substrate.Substrate.open(database) as sub:
        assert claims.review_verdicts_for(sub, statement.hash) == []
    with path.open("ab") as contender:
        fcntl.flock(contender.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(contender.fileno(), fcntl.LOCK_UN)
