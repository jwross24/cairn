import itertools
import math
import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from cairn import keys, pari, verifier
from cairn.verifier import AcceptPredicate, Instance, Submission, Verifier, VerifierConfig, VerifierConfigError, VerifierResult, default_config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _ec  # noqa: E402

CURVE60 = _ec.curve60()
X60 = 123456789
ROOT = Path(__file__).resolve().parent.parent.parent
OVERFLOW_STDERR = "***   stack overflow"
STARTUP_STDOUT = "### Errors on startup, exiting..."
TRUTH_RC = (0, 1, -9)
TRUTH_STDOUT = ("OK", "OK\n", 'FAIL ["xP-ne-Q"]', "", STARTUP_STDOUT)
TRUTH_STDERR = ("", OVERFLOW_STDERR)
TRUTH_TABLE = list(itertools.product(TRUTH_RC, TRUTH_STDOUT, TRUTH_STDERR))
STDOUT_LABELS = {"OK": "OK", "OK\n": "OK-newline", 'FAIL ["xP-ne-Q"]': "FAIL-line", "": "empty", STARTUP_STDOUT: "startup-errors"}
TRUTH_IDS = [f"rc{rc}-{STDOUT_LABELS[out]}-{'stderr-empty' if err == '' else 'stderr-overflow'}" for rc, out, err in TRUTH_TABLE]


def _inst60():
    return _ec.pair(CURVE60, X60)


def _outside_hasse(p):
    return p + 1 + math.isqrt(4 * p) + 1


REFUSALS = [
    ("arity-missing-Py", lambda i, x: (Instance(i.p, i.a, i.b, i.n, (i.P[0],), i.Q), x), "bad-arity"),
    ("arity-extra-Qz", lambda i, x: (Instance(i.p, i.a, i.b, i.n, i.P, i.Q + (1,)), x), "bad-arity"),
    ("arity-P-not-a-point", lambda i, x: (Instance(i.p, i.a, i.b, i.n, 5, i.Q), x), "bad-arity"),
    ("type-x-str", lambda i, x: (i, "3"), "bad-field"),
    ("type-x-float", lambda i, x: (i, 3.0), "bad-field"),
    ("type-x-bool", lambda i, x: (i, True), "bad-field"),
    ("type-x-none", lambda i, x: (i, None), "bad-field"),
    ("type-p-str", lambda i, x: (Instance(str(i.p), i.a, i.b, i.n, i.P, i.Q), x), "bad-field"),
    ("type-Qx-float", lambda i, x: (Instance(i.p, i.a, i.b, i.n, i.P, (float(i.Q[0]), i.Q[1])), x), "bad-field"),
    ("range-negative-x", lambda i, x: (i, -1), "bad-field"),
    ("range-negative-n", lambda i, x: (Instance(i.p, i.a, i.b, -i.n, i.P, i.Q), x), "bad-field"),
    ("range-p-2", lambda i, x: (Instance(2, 1, 1, 3, (0, 1), (0, 1)), 1), "bad-field"),
    ("range-p-3", lambda i, x: (Instance(3, 1, 1, 4, (0, 1), (0, 1)), 1), "bad-field"),
    ("range-p-0", lambda i, x: (Instance(0, 1, 1, 1, (0, 1), (0, 1)), 0), "bad-field"),
    ("range-x-eq-n", lambda i, x: (i, i.n), "bad-field"),
    ("range-x-gt-n", lambda i, x: (i, i.n + 1), "bad-field"),
    ("hasse-n-above", lambda i, x: (Instance(i.p, i.a, i.b, _outside_hasse(i.p), i.P, i.Q), x), "bad-field"),
    ("hasse-n-below", lambda i, x: (Instance(i.p, i.a, i.b, i.p + 1 - math.isqrt(4 * i.p) - 1, i.P, i.Q), x), "bad-field"),
    ("hasse-n-zero", lambda i, x: (Instance(i.p, i.a, i.b, 0, i.P, i.Q), 0), "bad-field"),
    ("submitter-named-P-and-Q", lambda i, x: (i, Submission(x, P=i.P, Q=i.Q)), "submitter-named-instance"),
    ("submitter-named-P-only", lambda i, x: (i, Submission(x, P=i.P)), "submitter-named-instance"),
    ("submitter-named-Q-only", lambda i, x: (i, Submission(x, Q=i.Q)), "submitter-named-instance"),
    ("submitter-named-with-bad-x", lambda i, x: (i, Submission("3", P=i.P, Q=i.Q)), "submitter-named-instance"),
]


@pytest.mark.parametrize(("label", "build", "expected"), REFUSALS, ids=[r[0] for r in REFUSALS])
def test_pre_spawn_refusal_table(popen_spy, run_gp_spy, label, build, expected):
    inst, x = build(*_inst60())
    result = Verifier().run(inst, x)
    assert isinstance(result, VerifierResult)
    assert (result.accepted, result.reason, result.reasons, result.rc, result.gate_result) == (False, expected, (expected,), None, "refused")
    assert result.stdout_digest is None and result.stderr_digest is None
    assert popen_spy == [] and run_gp_spy == []


def test_refusal_reasons_are_the_pre_spawn_vocabulary():
    assert {r[2] for r in REFUSALS} == set(verifier.PRE_SPAWN_REASONS)


@pytest.mark.parametrize(("rc", "stdout", "stderr"), TRUTH_TABLE, ids=TRUTH_IDS)
def test_accept_predicate_truth_table(rc, stdout, stderr):
    accepted, reason, reasons = verifier.classify(rc, stdout, stderr)
    expected_accept = rc == 0 and stdout.strip() == "OK" and stderr == ""
    assert accepted is expected_accept
    if expected_accept:
        assert (reason, reasons) == (None, ())
    elif stdout.startswith("FAIL "):
        assert (reason, reasons) == ("xP-ne-Q", ("xP-ne-Q",))
    else:
        assert (reason, reasons) == ("backend-crash", ("backend-crash",))


def test_truth_table_has_thirty_cells_and_exactly_two_accept():
    assert len(TRUTH_TABLE) == 30
    accepting = [cell for cell in TRUTH_TABLE if verifier.classify(*cell)[0]]
    assert accepting == [(0, "OK", ""), (0, "OK\n", "")]


@pytest.mark.parametrize(
    ("obj", "message"),
    [
        ({"stdout": "OK", "stderr_empty": True}, "missing"),
        ({"rc": 0, "stderr_empty": True}, "missing"),
        ({"rc": 0, "stdout": "OK"}, "missing"),
        ({}, "missing"),
        ({"rc": "0", "stdout": "OK", "stderr_empty": True}, "rc must be an int"),
        ({"rc": None, "stdout": "OK", "stderr_empty": True}, "rc must be an int"),
        ({"rc": True, "stdout": "OK", "stderr_empty": True}, "rc must be an int"),
        ({"rc": 0.0, "stdout": "OK", "stderr_empty": True}, "rc must be an int"),
        ({"rc": 0, "stdout": 1, "stderr_empty": True}, "stdout must be"),
        ({"rc": 0, "stdout": "OK", "stderr_empty": "yes"}, "stderr_empty must be"),
        ("rc=0", "mapping"),
    ],
    ids=["no-rc", "no-stdout", "no-stderr_empty", "empty", "rc-str", "rc-null", "rc-bool", "rc-float", "stdout-int", "stderr_empty-str", "not-a-mapping"],
)
def test_accept_predicate_refuses_missing_key_or_non_int_rc_at_construction(obj, message):
    with pytest.raises(VerifierConfigError, match=message):
        AcceptPredicate.from_dict(obj)


def test_accept_predicate_weaker_forms_are_legal_and_leave_the_field_unchecked():
    pinned = AcceptPredicate.from_dict({"rc": 0, "stdout": "OK", "stderr_empty": True})
    assert pinned == verifier.DEFAULT_ACCEPT and pinned.as_dict() == {"rc": 0, "stdout": "OK", "stderr_empty": True}
    no_stdout = AcceptPredicate.from_dict({"rc": 0, "stdout": None, "stderr_empty": True})
    no_stderr = AcceptPredicate.from_dict({"rc": 0, "stdout": "OK", "stderr_empty": False})
    overflow = (0, "", OVERFLOW_STDERR)
    assert not pinned.holds(*overflow)
    assert not no_stdout.holds(*overflow)
    assert not no_stderr.holds(*overflow)
    assert no_stdout.holds(0, "", "")
    assert no_stderr.holds(0, "OK\n", OVERFLOW_STDERR)
    assert AcceptPredicate.from_dict({"rc": 0, "stdout": None, "stderr_empty": False}).holds(*overflow)


def test_instance_reduces_coordinates_into_0_p_and_hashes_the_reduced_values():
    raw = Instance(5, -3, 1, 7, (0, 1), (3, 8))
    reduced = Instance(5, 2, 1, 7, (0, 1), (3, 3))
    assert (raw.a, raw.b, raw.P, raw.Q) == (2, 1, (0, 1), (3, 3))
    assert raw == reduced
    assert raw.instance_hash == reduced.instance_hash == keys.instance_hash({"p": 5, "a": 2, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 3]})
    assert raw.instance_hash != keys.instance_hash({"p": 5, "a": 2, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 8]})
    assert raw.fields(3) == (5, 2, 1, 7, 0, 1, 3, 3, 3)
    assert Instance(5, 2, 1, 7, [0, 1], [3, 3]).P == (0, 1)


def test_instance_with_a_junk_modulus_keeps_its_fields_and_has_no_hash():
    junk = Instance("5", -3, 1.5, None, (0, "1"), "Q")
    assert (junk.a, junk.b, junk.P, junk.Q) == (-3, 1.5, (0, "1"), "Q")
    assert verifier._hash_or_none(junk) is None
    assert junk.fields(3) == ("5", -3, 1.5, None, 0, "1", "Q", 3)


def test_render_line_is_decimal_on_one_line():
    inst, x = _inst60()
    line = verifier.render_line(inst.fields(x))
    assert line == f"verify({inst.p},{inst.a},{inst.b},{inst.n},{inst.P[0]},{inst.P[1]},{inst.Q[0]},{inst.Q[1]},{x})\n"
    assert line.count("\n") == 1 and "0x" not in line and "." not in line and "e" not in line.replace("verify", "")


def test_validate_fields_accepts_the_committed_60_bit_line_and_refuses_its_neighbors():
    inst, x = _inst60()
    fields = inst.fields(x)
    assert verifier.validate_fields(fields) is None
    assert verifier.validate_fields(fields[:-1] + (inst.n,)) == "bad-field"
    assert verifier.validate_fields(fields[:-1] + (inst.n - 1,)) is None
    assert verifier.validate_fields(fields + (1,)) == "bad-arity"
    assert verifier.validate_fields(()) == "bad-arity"
    assert verifier.validate_fields((4,) + fields[1:]) == "bad-field"
    assert verifier.validate_fields(fields[:3] + (inst.p + 1 + math.isqrt(4 * inst.p),) + fields[4:]) is None
    assert verifier.validate_fields(fields[:3] + (_outside_hasse(inst.p),) + fields[4:]) == "bad-field"


def test_fail_codes_reads_only_the_script_vocabulary_from_a_fail_line():
    assert verifier.fail_codes('FAIL ["P-off-curve", "Q-off-curve"]\n') == ("P-off-curve", "Q-off-curve")
    assert verifier.fail_codes('FAIL ["xP-ne-Q"]') == ("xP-ne-Q",)
    assert verifier.fail_codes("FAIL OK") == ()
    assert verifier.fail_codes('FAIL ["bad-field"]') == ()
    assert verifier.fail_codes('noise\nFAIL ["nQ-not-O"]\n') == ("nQ-not-O",)
    assert verifier.fail_codes("OK") == () and verifier.fail_codes(b"FAIL [\"xP-ne-Q\"]") == () and verifier.fail_codes(None) == ()


def test_reason_vocabulary_is_the_bead_list():
    assert set(verifier.REASONS) == {"p-not-prime", "singular", "P-off-curve", "Q-off-curve", "nQ-not-O", "xP-ne-Q", "backend-crash", "timeout", "bad-arity", "bad-field", "submitter-named-instance"}


def test_result_node_and_gate_result_shape():
    result = VerifierResult("ab" * 32, 3, True, None, (), "cd" * 32, "ef" * 32, 0, 0.017)
    assert result.node() == {"instance_hash": "ab" * 32, "x": 3, "accepted": True, "reason": None, "stdout_digest": "cd" * 32, "stderr_digest": "ef" * 32, "rc": 0, "wall_s": 0.017}
    assert result.gate_result == "pass"
    assert VerifierResult(None, 3, False, "bad-field", ("bad-field",), None, None, None, 0.0).gate_result == "refused"
    assert VerifierResult(None, 3, False, "backend-crash", ("backend-crash",), "x", "y", 0, 0.0).gate_result == "fail"
    assert VerifierResult(None, 3, False, "timeout", ("timeout",), None, None, None, 0.0).gate_result == "fail"


def test_config_defaults_and_bundle_form():
    cfg = default_config()
    assert (cfg.backend_path, cfg.stack_ceiling, cfg.timeout_s, cfg.accept) == (pari.GP_BIN, "64M", 30.0, verifier.DEFAULT_ACCEPT)
    assert cfg.script == (ROOT / "src" / "cairn" / "gp" / "verify.gp").read_bytes()
    assert cfg.bundle_hash == cfg.script_hash
    from_bundle = VerifierConfig.from_bundle({"backend_path": pari.GP_BIN, "stack_ceiling": "64M", "timeout_s": 30, "accept": {"rc": 0, "stdout": "OK", "stderr_empty": True}}, cfg.script, "ff" * 32)
    assert from_bundle.bundle_hash == "ff" * 32 and from_bundle.accept == verifier.DEFAULT_ACCEPT
    with pytest.raises(VerifierConfigError, match="missing"):
        VerifierConfig.from_bundle({"backend_path": pari.GP_BIN, "stack_ceiling": "64M", "timeout_s": 30}, cfg.script, "ff" * 32)
    with pytest.raises(VerifierConfigError, match="mapping"):
        VerifierConfig.from_bundle("backend_path=gp", cfg.script, "ff" * 32)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"stack_ceiling": "lots"}, "stack_ceiling"),
        ({"stack_ceiling": 64}, "stack_ceiling"),
        ({"timeout_s": 0}, "timeout_s"),
        ({"timeout_s": -1}, "timeout_s"),
        ({"timeout_s": "30"}, "timeout_s"),
        ({"accept": {"rc": 0, "stdout": "OK", "stderr_empty": True}}, "AcceptPredicate"),
        ({"script": b""}, "script"),
        ({"script": "verify"}, "script"),
        ({"backend_path": ""}, "backend_path"),
        ({"bundle_hash": ""}, "bundle_hash"),
    ],
    ids=["stack-word", "stack-int", "timeout-zero", "timeout-negative", "timeout-str", "accept-dict", "script-empty", "script-str", "backend-empty", "bundle-hash-empty"],
)
def test_config_refuses_malformed_fields_at_construction(overrides, message):
    with pytest.raises(VerifierConfigError, match=message):
        default_config(**overrides)


def test_verifier_refuses_a_backend_path_that_is_not_the_installed_gp():
    with pytest.raises(VerifierConfigError, match="backend_path"):
        Verifier(default_config(backend_path="/usr/bin/gp-other"))


def test_script_is_materialized_once_per_process_as_0444_outside_the_repo():
    cfg = default_config()
    path = verifier.materialize_script(cfg)
    again = verifier.materialize_script(cfg)
    assert path == again
    assert os.path.basename(path) == "verify.gp"
    assert os.path.basename(os.path.dirname(path)).startswith(f"cairn-bundle-{cfg.bundle_hash}-")
    assert Path(path).read_bytes() == cfg.script
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o444
    assert os.path.realpath(path).startswith(os.path.realpath(tempfile.gettempdir()))
    assert not os.path.realpath(path).startswith(str(ROOT))
    other = verifier.materialize_script(default_config(bundle_hash="11" * 32))
    assert other != path and os.path.basename(os.path.dirname(other)).startswith("cairn-bundle-" + "11" * 32)


def test_run_with_an_object_that_is_not_an_instance_is_refused(popen_spy, run_gp_spy):
    result = Verifier().run(object(), 3)
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, "bad-field", None, "refused")
    assert popen_spy == [] and run_gp_spy == []


def test_crash_selftest_refuses_a_bad_instance_pre_spawn(popen_spy, run_gp_spy):
    result = Verifier().crash_selftest(Instance(2, 1, 1, 3, (0, 1), (0, 1)))
    assert (result.accepted, result.reason, result.rc, result.gate_result) == (False, "bad-field", None, "refused")
    assert popen_spy == [] and run_gp_spy == []


def test_a_stale_materialized_path_is_rematerialized():
    cfg = default_config(bundle_hash="22" * 32)
    path = verifier.materialize_script(cfg)
    os.remove(path)
    fresh = verifier.materialize_script(cfg)
    assert Path(fresh).read_bytes() == cfg.script
    assert stat.S_IMODE(os.stat(fresh).st_mode) == 0o444


def test_verifier_registers_no_cli_subcommand():
    from cairn import cli

    assert "verifier" not in cli.COMMAND_MODULES
    assert not any("verif" in name for name in cli.registered())
