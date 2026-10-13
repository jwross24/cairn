import errno
import json
import subprocess

import pytest

from cairn import solutionbuild


@pytest.fixture
def dependency_project(tmp_path):
    package = tmp_path / ".lake" / "packages" / "mathlib"
    (package / ".git").mkdir(parents=True)
    manifest = {
        "packagesDir": ".lake/packages",
        "packages": [{"name": "mathlib", "type": "git", "rev": "test-revision", "url": "test-origin"}],
    }
    (tmp_path / "lake-manifest.json").write_text(json.dumps(manifest))
    return tmp_path, package, manifest, {"mathlib_rev": "test-revision"}


def _diagnostics(path):
    return [
        record
        for line in path.read_text().splitlines()
        if (record := json.loads(line)).get("step") == "solutionbuild"
        and record.get("event") == "dependency_checkout_unreadable"
    ]


@pytest.mark.parametrize("query_index", range(3), ids=("revision", "origin", "status"))
@pytest.mark.parametrize("exception_class", [OSError, subprocess.TimeoutExpired], ids=("os-error", "timeout"))
def test_unreadable_dependency_logs_exact_query_and_exception(
    dependency_project, monkeypatch, json_test_log, query_index, exception_class
):
    project, package, manifest, pins = dependency_project
    commands = [[solutionbuild.GIT, "-C", str(package), *query] for query in solutionbuild.DEPENDENCY_QUERIES]
    failed_command = commands[query_index]
    original = (
        OSError(errno.EIO, "simulated dependency I/O failure", str(package))
        if exception_class is OSError
        else subprocess.TimeoutExpired(failed_command, 10, output=b"partial output", stderr=b"partial stderr")
    )
    calls = []

    def run(argv, **kwargs):
        assert argv == commands[len(calls)]
        assert kwargs["timeout"] == 10
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        assert kwargs["capture_output"] is True and kwargs["text"] is True and kwargs["check"] is False
        calls.append(argv)
        if len(calls) - 1 == query_index:
            raise original
        return subprocess.CompletedProcess(argv, 0, ("test-revision\n", "test-origin\n", "")[len(calls) - 1], "")

    monkeypatch.setattr(solutionbuild.subprocess, "run", run)
    with pytest.raises(solutionbuild.SolutionRefused) as caught:
        solutionbuild._dependency_packages(project, manifest, pins)
    query = list(solutionbuild.DEPENDENCY_QUERIES[query_index])
    records = _diagnostics(json_test_log)
    assert records, f"missing dependency diagnostic for query {query!r}"
    assert len(records) == 1
    record = records[0]
    assert record["level"] == "WARNING"
    assert record["package"] == "mathlib"
    assert record["query"] == query
    assert record["argv"] == failed_command
    assert record["exception_class"] == exception_class.__name__
    assert record["error"] == str(original)
    assert caught.value.reason.encode() == b"dependency-checkout-unreadable:mathlib"
    assert str(caught.value).encode() == b"dependency-checkout-unreadable:mathlib"
    assert caught.value.__cause__ is original
    assert calls == commands[: query_index + 1]


def test_valid_dependencies_pass_without_failure_diagnostic(dependency_project, monkeypatch, json_test_log):
    project, package, manifest, pins = dependency_project
    calls = []
    commands = [[solutionbuild.GIT, "-C", str(package), *query] for query in solutionbuild.DEPENDENCY_QUERIES]

    def run(argv, **kwargs):
        assert argv == commands[len(calls)]
        assert kwargs["timeout"] == 10
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, ("test-revision\n", "test-origin\n", "")[len(calls) - 1], "")

    monkeypatch.setattr(solutionbuild.subprocess, "run", run)
    assert solutionbuild._dependency_packages(project, manifest, pins) == [package]
    assert calls == commands
    assert _diagnostics(json_test_log) == []
