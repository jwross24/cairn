from pathlib import Path

import pytest

CONFTEST_SRC = (Path(__file__).resolve().parent.parent / "conftest.py").read_text()


def test_differing_golden_fails_with_a_diff_and_writes_actual(assert_golden, tmp_path, monkeypatch):
    monkeypatch.delenv("UPDATE_GOLDENS", raising=False)
    golden = tmp_path / "x.golden"
    golden.write_text("old\n")
    with pytest.raises(AssertionError) as info:
        assert_golden(golden, "new\n")
    assert "-old" in str(info.value) and "+new" in str(info.value)
    assert (tmp_path / "x.golden.actual").read_text() == "new\n"


def test_update_goldens_rewrites_the_file(assert_golden, tmp_path, monkeypatch):
    monkeypatch.setenv("UPDATE_GOLDENS", "1")
    golden = tmp_path / "y.golden"
    golden.write_text("old\n")
    assert_golden(golden, "new\n")
    assert golden.read_text() == "new\n"


def test_isolation_guard_fails_a_test_that_writes_under_deploy(pytester, monkeypatch):
    monkeypatch.setenv("CAIRN_REPO_ROOT", str(pytester.path))
    pytester.makeconftest(CONFTEST_SRC)
    pytester.makepyfile(
        """
        import pathlib
        def test_writes_deploy():
            pathlib.Path("deploy").mkdir(exist_ok=True)
            pathlib.Path("deploy/leak").write_text("x")
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(passed=1, errors=1)
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*IsolationViolation*deploy/leak*"])


def test_isolation_guard_fails_a_test_that_spawns_outside_the_allow_list(pytester, monkeypatch):
    monkeypatch.setenv("CAIRN_REPO_ROOT", str(pytester.path))
    pytester.makeconftest(CONFTEST_SRC)
    pytester.makepyfile(
        """
        import subprocess
        def test_spawns_echo():
            subprocess.run(["/bin/echo", "hi"], check=True)
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*IsolationViolation*/bin/echo*"])


def test_isolation_guard_admits_only_the_exact_read_only_dependency_queries(pytester, monkeypatch):
    monkeypatch.setenv("CAIRN_REPO_ROOT", str(pytester.path))
    pytester.makeconftest(CONFTEST_SRC)
    pytester.makepyfile(
        """
        import subprocess
        import pytest

        def test_read_only_query():
            result = subprocess.run(
                ["/usr/bin/git", "-C", "/nonexistent-cairn-dependency", "rev-parse", "HEAD"],
                capture_output=True,
            )
            assert result.returncode != 0
            assert b"cannot change to" in result.stderr

        @pytest.mark.parametrize("tail", [
            ["config", "test.value", "changed"],
            ["status", "--porcelain", "--untracked-files=normal", "--short"],
            ["remote", "set-url", "origin", "https://example.invalid"],
        ])
        def test_mutation_or_extra_flags_are_denied(tail):
            subprocess.run(["/usr/bin/git", "-C", ".", *tail])
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(passed=1, failed=3)
    result.stdout.fnmatch_lines(["*IsolationViolation*/usr/bin/git*"])


def test_isolation_guard_bounds_the_native_rss_commands(pytester, monkeypatch):
    monkeypatch.setenv("CAIRN_REPO_ROOT", str(pytester.path))
    pytester.makeconftest(CONFTEST_SRC)
    pytester.makepyfile(
        """
        import socket
        import subprocess
        import sys
        import pytest
        from cairn import rss
        from conftest import IsolationViolation

        def test_native_reporter_or_platform_refusal(tmp_path):
            if sys.platform != "linux":
                with pytest.raises(rss.ReporterError, match="requires Linux"):
                    rss.build_binary()
                return
            out = tmp_path / "stdout"
            err = tmp_path / "stderr"
            rss.spawn_and_wait(
                [sys.executable, "-c", "print(123)"], out, err,
                wall_cap_s=5, env=None, stdin_bytes=b"", tick=0.01,
                grace=0.1, is_yanked=None,
            )
            assert out.read_bytes() == b"123\\n"

        def test_direct_compiler_is_refused():
            with pytest.raises(IsolationViolation, match="outside the allow-list"):
                subprocess.run([str(rss.COMPILER), "--version"], capture_output=True)

        def test_reporter_cannot_launder_an_unlisted_worker(tmp_path):
            if sys.platform != "linux":
                with pytest.raises(IsolationViolation, match="outside the allow-list"):
                    subprocess.run(["/proc/self/fd/999", "1", "999", "/bin/echo"])
                return
            with pytest.raises(IsolationViolation, match="reporter worker outside"):
                rss.spawn_and_wait(
                    ["/bin/echo", "forbidden"], tmp_path / "out", tmp_path / "err",
                    wall_cap_s=5, env=None, stdin_bytes=b"", tick=0.01,
                    grace=0.1, is_yanked=None,
                )

        def test_reporter_requires_the_exact_process_envelope():
            if sys.platform != "linux":
                with pytest.raises(IsolationViolation, match="outside the allow-list"):
                    subprocess.run(["/proc/self/fd/999", "1", "999", sys.executable])
                return
            binary = rss.build_binary()
            receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            with receiver, sender:
                command = [binary.path, str(sender.fileno()), str(binary.fd), sys.executable]
                kwargs = dict(pass_fds=(sender.fileno(), binary.fd), close_fds=True,
                              start_new_session=True)
                for change in (dict(pass_fds=(binary.fd,)), dict(start_new_session=False),
                               dict(executable=sys.executable)):
                    with pytest.raises(IsolationViolation, match="outside the allow-list"):
                        subprocess.Popen(command, **(kwargs | change))
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(passed=4)
