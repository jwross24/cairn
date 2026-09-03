from pathlib import Path

import _libpari_stall

TESTS = Path(__file__).resolve().parents[1]
HOOK_CONFTEST = "from _libpari_stall import pytest_runtest_protocol\n"
INNER_ARGS = ("-p", "no:cacheprovider", "-p", "no:faulthandler")


def test_the_hook_is_registered_in_this_session(request):
    impls = request.config.pluginmanager.hook.pytest_runtest_protocol.get_hookimpls()
    assert any(impl.function is _libpari_stall.pytest_runtest_protocol for impl in impls)


def test_a_late_alarm_interrupt_escaping_a_test_ends_the_session_the_same_way(pytester):
    pytester.syspathinsert(str(TESTS))
    pytester.makeconftest(HOOK_CONFTEST)
    pytester.makepyfile(
        """
        from cysignals.alarm import AlarmInterrupt


        def test_late_alarm():
            raise AlarmInterrupt()
        """
    )
    result = pytester.runpytest(*INNER_ARGS)
    assert result.ret == 124
    result.stdout.fnmatch_lines(["*libpari bound fired after its call returned in test_*.py::test_late_alarm*"])


def test_a_stall_escaping_a_test_ends_the_session_at_exit_124_before_the_next_test(pytester):
    pytester.syspathinsert(str(TESTS))
    pytester.makeconftest(HOOK_CONFTEST)
    marker = pytester.path / "second-test-ran"
    pytester.makepyfile(
        f"""
        from pathlib import Path

        from cairn import pari


        def test_first_stalls():
            raise pari.PariStall("ellsea", 60.0, 60.3)


        def test_second_never_runs():
            Path({str(marker)!r}).write_text("ran")
        """
    )
    result = pytester.runpytest(*INNER_ARGS)
    assert result.ret == 124
    result.stdout.fnmatch_lines(
        ["*libpari stall in test_*.py::test_first_stalls: libpari stall: ellsea passed the 60 s in-process bound*"]
    )
    assert not marker.exists()


def test_a_stall_escaping_a_fixture_ends_the_session_the_same_way(pytester):
    pytester.syspathinsert(str(TESTS))
    pytester.makeconftest(HOOK_CONFTEST)
    pytester.makepyfile(
        """
        import pytest

        from cairn import pari


        @pytest.fixture
        def curve():
            raise pari.PariStall("ellcard", 60.0, 61.0)


        def test_uses_the_curve(curve):
            pass
        """
    )
    result = pytester.runpytest(*INNER_ARGS)
    assert result.ret == 124
    result.stdout.fnmatch_lines(["*libpari stall in test_*.py::test_uses_the_curve: libpari stall: ellcard*"])


def test_an_ordinary_keyboard_interrupt_keeps_pytest_s_own_exit(pytester):
    pytester.syspathinsert(str(TESTS))
    pytester.makeconftest(HOOK_CONFTEST)
    pytester.makepyfile("def test_interrupts():\n    raise KeyboardInterrupt\n")
    # pytester re-raises an inner KeyboardInterrupt into the outer session unless told not to.
    result = pytester.runpytest(*INNER_ARGS, no_reraise_ctrlc=True)
    assert result.ret == 2
    assert "libpari stall" not in result.stdout.str()
