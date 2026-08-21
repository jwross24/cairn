import json
import math
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from cairn import verifier
from cairn.verifier import Instance, Submission, Verifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _ec  # noqa: E402
from mutants import verifier_mutants  # noqa: E402

CORPUS = Path(__file__).resolve().parent.parent / "fuzz_corpus" / "verifier"
CURVE60 = _ec.curve60()
X60 = 123456789
BASE_INSTANCE, _ = _ec.pair(CURVE60, X60)
BASE_FIELDS = BASE_INSTANCE.fields(X60)
P60, N60 = CURVE60["p"], CURVE60["n"]
OVERFLOW_8M = (0, "", "  *** ellcard: the PARI stack overflows !\n  current stack size: 8000000 (7.629 Mbytes)\n")
STARTUP_2M = (1, "### Errors on startup, exiting...\n\n\n", "  ***   the PARI stack overflows !\n")
fixture_ok = settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

junk = st.one_of(st.integers(-(2**300), 2**300), st.text(), st.binary(), st.floats(), st.none(), st.booleans())
junk_fields = st.lists(junk, min_size=0, max_size=12)
points = st.one_of(st.lists(junk, min_size=0, max_size=4), junk)
io_text = st.one_of(st.text(), st.binary())


def _corpus(kind):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CORPUS.glob(f"{kind}_*.json"))]


def _with(field, value):
    i = verifier.FIELD_NAMES.index(field)
    return BASE_FIELDS[:i] + (value,) + BASE_FIELDS[i + 1 :]


TARGETED_FIELDS = [
    _with("x", N60),
    _with("x", N60 - 1),
    _with("p", 2),
    _with("p", 3),
    _with("n", P60 + 1 + 2 * math.isqrt(P60) + 1),
    _with("a", P60),
]


def check_validator(fields):
    reason = verifier.validate_fields(fields)
    assert reason in (None, "bad-arity", "bad-field")
    if len(fields) != verifier.ARITY:
        assert reason == "bad-arity"
    elif reason is None:
        assert all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in fields)
        assert not _ec.breaks_pre_spawn_rules(fields)


def check_run_fields(fields, spy):
    before = len(spy)
    result = Verifier().run_fields(fields)
    assert result.accepted in (False, True)
    if result.reason in verifier.PRE_SPAWN_REASONS:
        assert result.accepted is False and result.gate_result == "refused" and result.rc is None
        assert len(spy) == before
    else:
        assert len(spy) == before + 1
        assert result.reason is None if result.accepted else result.reason in verifier.SCRIPT_REASONS + verifier.BACKEND_REASONS


def check_run(instance, x, spy):
    before = len(spy)
    result = Verifier().run(instance, x)
    if result.reason in verifier.PRE_SPAWN_REASONS:
        assert result.accepted is False and result.gate_result == "refused"
        assert len(spy) == before
        if isinstance(x, Submission) and x.names_instance:
            assert result.reason == "submitter-named-instance"
    else:
        assert len(spy) == before + 1


def check_classifier(rc, stdout, stderr):
    accepted, reason, reasons = verifier.classify(rc, stdout, stderr)
    assert accepted == (rc == 0 and stdout.strip() == "OK" and stderr == ""), f"accepted={accepted} for rc={rc!r} stdout={stdout!r} stderr={stderr!r}"
    if accepted:
        assert (reason, reasons) == (None, ())
        return
    assert reason in verifier.REASONS and reason not in verifier.PRE_SPAWN_REASONS and reason != "timeout"
    assert reasons and reasons[0] == reason and all(r in verifier.REASONS for r in reasons)
    if reason in verifier.SCRIPT_REASONS:
        assert isinstance(stdout, str) and any(line.startswith("FAIL ") for line in stdout.splitlines())
    else:
        assert reason == "backend-crash"


test_validator_never_raises_on_any_field_list = given(junk_fields)(check_validator)
for _fields in TARGETED_FIELDS + [c["fields"] for c in _corpus("fields")]:
    test_validator_never_raises_on_any_field_list = example(list(_fields))(test_validator_never_raises_on_any_field_list)


@fixture_ok
@given(junk_fields)
def test_run_fields_never_spawns_on_a_refusal_and_never_raises(run_gp_spy, fields):
    check_run_fields(tuple(fields), run_gp_spy)


for _fields in TARGETED_FIELDS + [c["fields"] for c in _corpus("fields")]:
    test_run_fields_never_spawns_on_a_refusal_and_never_raises = example(list(_fields))(test_run_fields_never_spawns_on_a_refusal_and_never_raises)


@fixture_ok
@given(p=junk, a=junk, b=junk, n=junk, P=points, Q=points, x=st.one_of(junk, st.builds(Submission, junk, st.none() | points, st.none() | points)))
@example(p=P60, a=CURVE60["a"], b=CURVE60["b"], n=N60, P=list(CURVE60["P"]), Q=list(BASE_INSTANCE.Q), x=Submission(X60, P=list(CURVE60["P"]), Q=list(BASE_INSTANCE.Q)))
@example(p=P60, a=CURVE60["a"], b=CURVE60["b"], n=N60, P=list(CURVE60["P"]), Q=list(BASE_INSTANCE.Q), x=N60)
@example(p=2, a=1, b=1, n=3, P=[0, 1], Q=[0, 1], x=1)
def test_run_on_junk_instances_never_spawns_on_a_refusal_and_never_raises(run_gp_spy, p, a, b, n, P, Q, x):
    check_run(Instance(p, a, b, n, P, Q), x, run_gp_spy)


test_classifier_accepts_exactly_rc0_ok_empty_stderr = given(st.integers(-64, 255), io_text, io_text)(check_classifier)
for _rc, _out, _err in [OVERFLOW_8M, STARTUP_2M, (-9, "", ""), (0, "OK\n", "warning\n"), (1, 'FAIL ["xP-ne-Q"]\n', ""), (0, "FAIL OK", ""), (0, "NOT OK", ""), (0, "OK\nextra", ""), (0, "OK", "x"), (0, "OK\n", ""), (0, b"OK", b"")] + [(c["rc"], c["stdout"], c["stderr"]) for c in _corpus("classify")]:
    test_classifier_accepts_exactly_rc0_ok_empty_stderr = example(_rc, _out, _err)(test_classifier_accepts_exactly_rc0_ok_empty_stderr)


def test_mutant_accept_rc0_only_is_killed_by_the_classifier_property():
    check_classifier(*OVERFLOW_8M)
    with verifier_mutants.accept_rc0_only(), pytest.raises(AssertionError, match="accepted=True"):
        check_classifier(*OVERFLOW_8M)


@pytest.mark.parametrize(("rc", "stdout", "stderr"), [(0, "FAIL OK", ""), (0, "NOT OK", ""), (0, "OK\nextra", ""), (0, "OK", "stderr bytes")], ids=["FAIL-OK", "NOT-OK", "OK-extra-line", "OK-with-stderr"])
def test_mutant_accept_if_OK_substring_is_killed_by_the_classifier_property(rc, stdout, stderr):
    check_classifier(rc, stdout, stderr)
    with verifier_mutants.accept_if_OK_substring(), pytest.raises(AssertionError, match="accepted=True"):
        check_classifier(rc, stdout, stderr)


@pytest.mark.parametrize("case", _corpus("classify"), ids=lambda c: f"rc{c['rc']}-{c['expect']['reason'] or 'accept'}")
def test_fuzz_corpus_classify_replay(case):
    accepted, reason, _reasons = verifier.classify(case["rc"], case["stdout"], case["stderr"])
    assert (accepted, reason) == (case["expect"]["accepted"], case["expect"]["reason"])


@pytest.mark.parametrize("case", _corpus("fields"), ids=lambda c: c["expect"] + "-" + str(len(c["fields"])))
def test_fuzz_corpus_fields_replay(run_gp_spy, case):
    assert verifier.validate_fields(case["fields"]) == case["expect"]
    result = Verifier().run_fields(case["fields"])
    assert (result.accepted, result.reason, result.gate_result) == (False, case["expect"], "refused")
    assert run_gp_spy == []


def test_corpus_holds_every_planted_negative_the_bead_names():
    names = {p.stem for p in CORPUS.glob("*.json")}
    assert {
        "classify_overflow_8m",
        "classify_startup_2m",
        "classify_killed_rc_minus_9",
        "classify_ok_with_stderr_bytes",
        "classify_fail_xp_ne_q",
        "fields_ten_field_line",
        "fields_negative_int",
        "fields_p_equals_2",
        "fields_x_equals_n",
        "fields_n_outside_hasse",
        "fields_arabic_indic_digit",
        "fields_scientific_1e3",
        "fields_hex_0x1f",
        "fields_leading_space_3",
        "fields_trailing_newline_3",
        "fields_a_equals_p",
        "fields_Px_equals_p",
        "fields_Qy_equals_p",
    } <= names
