import logging
import math
import os
import random
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import log, pari, verifier
from cairn.verifier import Instance, Submission, Verifier, default_config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _ec  # noqa: E402

CURVE60 = _ec.curve60()
X60 = 123456789
STACKS_WHERE_VERIFY_IS_OK = ("3M", "8M", "64M")
CRASH_STACK = "8M"
CONTROL_STACK = "64M"
STARTUP_OVERFLOW_STACK = "2M"
STARTUP_FAIL_STDOUT = "### Errors on startup, exiting..."
OVERFLOW_FRAGMENT = "ellcard: the PARI stack overflows !"
RANDOM_DRAWS = 20


def _inst60():
    return _ec.pair(CURVE60, X60)


def _fact(lg, label, stack, line, result, spy):
    call = spy[-1]
    lg.info(
        "gp_fact",
        label=label,
        command=f"{' '.join(pari.gp_argv(stack) + call['args'])} <<< {call['stdin'].strip()!r}",
        stack=stack,
        stdin=call["stdin"].strip(),
        rc=result.rc,
        accepted=result.accepted,
        reason=result.reason,
        gp_bin=pari.GP_BIN,
        line=line,
    )


@pytest.fixture
def gp_io(monkeypatch):
    seen = []
    real = pari.run_gp

    def spy(args, stdin, **kw):
        rc, out, err = real(args, stdin, **kw)
        seen.append({"args": list(args), "stdin": stdin, "rc": rc, "stdout": out, "stderr": err, **kw})
        return rc, out, err

    monkeypatch.setattr(pari, "run_gp", spy)
    return seen


def test_corpus_case_1_is_ok_and_reaches_gp_with_a_reduced(gp_io):
    c = _ec.CORPUS_1
    inst = Instance(c["p"], c["a"], c["b"], c["n"], c["P"], c["Q"])
    assert inst.a == 2
    result = Verifier().run(inst, c["x"])
    assert (result.accepted, result.reason, result.rc) == (True, None, 0)
    assert gp_io[-1]["stdin"] == "verify(5,2,1,7,0,1,3,3,3)\n"
    assert (gp_io[-1]["stdout"], gp_io[-1]["stderr"]) == ("OK\n", "")


def test_gp_cypari2_plumbing_one_library_twice(gp_io):
    inst, x = _inst60()
    result = Verifier().run(inst, x)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (True, None, 0, "pass")
    assert result.instance_hash == inst.instance_hash
    assert result.x == x
    assert gp_io[-1]["stdin"] == verifier.render_line(inst.fields(x))
    assert (gp_io[-1]["stdout"], gp_io[-1]["stderr"]) == ("OK\n", "")
    assert gp_io[-1]["args"][0].endswith("/verify.gp")


@pytest.mark.parametrize(
    ("label", "mutate", "expected"),
    [
        ("Qy-plus-1-off-curve", lambda inst, x: (Instance(inst.p, inst.a, inst.b, inst.n, inst.P, (inst.Q[0], inst.Q[1] + 1)), x), "Q-off-curve"),
        ("other-on-curve-point", lambda inst, x: (_ec.instance(CURVE60, _ec.mul(CURVE60, CURVE60["P"], x + 1)), x), "xP-ne-Q"),
        ("x-plus-1", lambda inst, x: (inst, x + 1), "xP-ne-Q"),
        ("n-plus-2-inside-hasse", lambda inst, x: (Instance(inst.p, inst.a, inst.b, inst.n + 2, inst.P, inst.Q), x), "nQ-not-O"),
        ("Py-plus-1-off-curve", lambda inst, x: (Instance(inst.p, inst.a, inst.b, inst.n, (inst.P[0], inst.P[1] + 1), inst.Q), x), "P-off-curve"),
        ("p-composite-25", lambda inst, x: (Instance(25, 1, 1, 26, (0, 1), (0, 1)), 1), "p-not-prime"),
        ("singular-curve", lambda inst, x: (Instance(5, 0, 0, 6, (0, 0), (0, 0)), 1), "singular"),
        ("corpus-1-x-4", lambda inst, x: (Instance(5, 2, 1, 7, (0, 1), (3, 3)), 4), "xP-ne-Q"),
    ],
)
def test_planted_negatives_fail_with_the_script_reason(gp_io, label, mutate, expected):
    inst, x = mutate(*_inst60())
    assert (inst.n - inst.p - 1) ** 2 <= 4 * inst.p
    result = Verifier().run(inst, x)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, expected, 1, "fail")
    assert gp_io[-1]["stdout"].startswith(f'FAIL ["{expected}"]') or expected in gp_io[-1]["stdout"]
    assert gp_io[-1]["stderr"] == ""


def test_crash_selftest_at_8M_is_backend_crash_and_64M_control_is_ok(gp_io):
    lg = log.get("verifier.test")
    inst, _x = _inst60()
    crash = Verifier(default_config(stack_ceiling=CRASH_STACK)).crash_selftest(inst)
    _fact(lg, "crash_selftest-8M", CRASH_STACK, gp_io[-1]["stdin"], crash, gp_io)
    lg.info("crash_io", rc=gp_io[-1]["rc"], stdout=gp_io[-1]["stdout"], stderr=gp_io[-1]["stderr"])
    assert (gp_io[-1]["rc"], gp_io[-1]["stdout"]) == (0, "")
    assert OVERFLOW_FRAGMENT in gp_io[-1]["stderr"]
    assert (crash.accepted, crash.reason, crash.rc, crash.gate_result) == (False, "backend-crash", 0, "fail")
    control = Verifier(default_config(stack_ceiling=CONTROL_STACK)).crash_selftest(inst)
    _fact(lg, "crash_selftest-64M", CONTROL_STACK, gp_io[-1]["stdin"], control, gp_io)
    assert (gp_io[-1]["rc"], gp_io[-1]["stdout"], gp_io[-1]["stderr"]) == (0, "OK\n", "")
    assert (control.accepted, control.reason, control.rc) == (True, None, 0)
    assert gp_io[-1]["stdin"] == f"crash_selftest({inst.p},{inst.a},{inst.b})\n"


@pytest.mark.parametrize("stack", STACKS_WHERE_VERIFY_IS_OK)
def test_verify_is_ok_at_3M_8M_64M_on_curve60(gp_io, stack):
    lg = log.get("verifier.test")
    inst, x = _inst60()
    result = Verifier(default_config(stack_ceiling=stack)).run(inst, x)
    _fact(lg, f"verify-{stack}", stack, gp_io[-1]["stdin"], result, gp_io)
    assert (gp_io[-1]["rc"], gp_io[-1]["stdout"], gp_io[-1]["stderr"]) == (0, "OK\n", "")
    assert (result.accepted, result.reason, result.rc) == (True, None, 0)


def test_startup_overflow_at_2M_is_backend_crash(gp_io):
    lg = log.get("verifier.test")
    inst, x = _inst60()
    result = Verifier(default_config(stack_ceiling=STARTUP_OVERFLOW_STACK)).run(inst, x)
    _fact(lg, "verify-2M", STARTUP_OVERFLOW_STACK, gp_io[-1]["stdin"], result, gp_io)
    assert gp_io[-1]["rc"] == 1
    assert gp_io[-1]["stdout"].startswith(STARTUP_FAIL_STDOUT)
    assert "the PARI stack overflows" in gp_io[-1]["stderr"]
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, "backend-crash", 1, "fail")


def test_killed_child_rc_minus_9_is_backend_crash(monkeypatch):
    base = subprocess.Popen

    class KillAfterSpawn(base):
        def __init__(self, args, *a, **kw):
            super().__init__(args, *a, **kw)
            os.kill(self.pid, signal.SIGKILL)

    monkeypatch.setattr(subprocess, "Popen", KillAfterSpawn)
    inst, x = _inst60()
    result = Verifier().run(inst, x)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, "backend-crash", -signal.SIGKILL, "fail")


def test_timeout_on_a_good_instance_is_timeout():
    inst, x = _inst60()
    result = Verifier(default_config(timeout_s=0.001)).run(inst, x)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, "timeout", None, "fail")
    assert result.stdout_digest is None and result.stderr_digest is None


def test_p_equals_2_is_refused_before_any_spawn(popen_spy, run_gp_spy):
    result = Verifier().run(Instance(2, 1, 1, 3, (0, 1), (0, 1)), 1)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, "bad-field", None, "refused")
    assert popen_spy == [] and run_gp_spy == []


def _outside_hasse(p):
    return p + 1 + math.isqrt(4 * p) + 1


@pytest.mark.parametrize(
    ("label", "build", "expected"),
    [
        ("missing-field-P-has-one-coordinate", lambda inst, x: (Instance(inst.p, inst.a, inst.b, inst.n, (inst.P[0],), inst.Q), x), "bad-arity"),
        ("extra-field-Q-has-three-coordinates", lambda inst, x: (Instance(inst.p, inst.a, inst.b, inst.n, inst.P, inst.Q + (1,)), x), "bad-arity"),
        ("negative-int-x", lambda inst, x: (inst, -1), "bad-field"),
        ("x-equals-n", lambda inst, x: (inst, inst.n), "bad-field"),
        ("x-above-n", lambda inst, x: (inst, inst.n + 5), "bad-field"),
        ("n-outside-hasse", lambda inst, x: (Instance(inst.p, inst.a, inst.b, _outside_hasse(inst.p), inst.P, inst.Q), x), "bad-field"),
        ("p-equals-3", lambda inst, x: (Instance(3, 1, 1, 4, (0, 1), (0, 1)), 1), "bad-field"),
        ("x-is-a-string", lambda inst, x: (inst, str(x)), "bad-field"),
        ("x-is-a-float", lambda inst, x: (inst, float(x)), "bad-field"),
        ("submission-names-P-and-Q", lambda inst, x: (inst, Submission(x, P=inst.P, Q=inst.Q)), "submitter-named-instance"),
        ("submission-names-Q-only", lambda inst, x: (inst, Submission(x, Q=inst.Q)), "submitter-named-instance"),
    ],
)
def test_pre_spawn_refusals_spawn_nothing(popen_spy, run_gp_spy, label, build, expected):
    inst, x = build(*_inst60())
    result = Verifier().run(inst, x)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, expected, None, "refused")
    assert popen_spy == [] and run_gp_spy == []


def test_submission_with_bare_x_is_verified(gp_io):
    inst, x = _inst60()
    result = Verifier().run(inst, Submission(x))
    assert (result.accepted, result.x) == (True, x)
    assert len(gp_io) == 1


def test_randomized_arm_twenty_ok_and_twenty_fail():
    rng = random.Random(1)
    n = CURVE60["n"]
    v = Verifier()
    for _ in range(RANDOM_DRAWS):
        x = rng.randrange(1, n)
        inst, x = _ec.pair(CURVE60, x)
        assert v.run(inst, x).accepted is True
        other = rng.randrange(1, n)
        while other == x:
            other = rng.randrange(1, n)
        wrong = v.run(inst, other)
        assert (wrong.accepted, wrong.reason) == (False, "xP-ne-Q")


def test_every_run_logs_exactly_one_verdict_record(caplog):
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    inst, x = _inst60()
    v = Verifier()
    runs = [v.run(inst, x), v.run(inst, x + 1), v.run(Instance(2, 1, 1, 3, (0, 1), (0, 1)), 1), v.run(inst, Submission(x, P=inst.P, Q=inst.Q))]
    verdicts = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "verdict" and r.step == "verifier"]
    assert len(verdicts) == len(runs)
    assert [r.fields["reason"] for r in verdicts] == [None, "xP-ne-Q", "bad-field", "submitter-named-instance"]
    assert all({"instance_hash", "accepted", "reason", "rc", "wall_ms"} <= set(r.fields) for r in verdicts)
    assert all(r.levelno == logging.INFO for r in verdicts)
