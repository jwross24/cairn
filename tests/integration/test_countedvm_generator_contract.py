import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import countedvm, ec, pari, verifier
from cairn.countedvm import programs

INSTANCE = countedvm.Instance(101, 90, 44, 89, (2, 38), (12, 23))
BUDGET = 100_000
CALLS = []


class _HiddenCurveBounds(dict):
    def items(self):
        return {"max_outer": 0}.items()


def _generator(n, seed, bounds):
    CALLS.append({"n": n, "seed": seed, "bounds": bounds.copy()})
    return programs.bsgs_program(n, seed=seed)


def _keyword_generator(*, n, seed, bounds):
    return _generator(n, seed, bounds)


def _kwargs_generator(**kwargs):
    assert set(kwargs) == {"n", "seed", "bounds"}
    return _generator(**kwargs)


def _optional_generator(n, seed, bounds, p=None):
    assert p is None
    return _generator(n, seed, bounds)


def _called_program():
    CALLS.append(True)
    return "halt\n"


def _requires_p(n, seed, bounds, p):
    return _called_program()


def _requires_a(n, seed, bounds, a):
    return _called_program()


def _requires_b(n, seed, bounds, b):
    return _called_program()


def _requires_P(n, seed, bounds, P):
    return _called_program()


def _requires_Q(n, seed, bounds, Q):
    return _called_program()


def _requires_other(n, seed, bounds, other):
    return _called_program()


def _positional_generator(n, seed, bounds, /):
    CALLS.append(True)
    return "halt\n"


def _bad_result_generator(n, seed, bounds):
    CALLS.append(True)
    return 123


def _r6_advice_generator(n, seed, bounds, p, a, b, P):
    CALLS.append(True)
    assert ec.is_on_curve(p, a, b, tuple(P))
    rows = bounds["rows"]
    assert rows == 128 and p < rows
    advice = [0] * rows
    point = None
    for scalar in range(n):
        if point is not None:
            advice[point[0]] = scalar
        point = ec.add(p, a, point, tuple(P))
    lines = ["setp p6 P", "setp p7 Q", "setp p8 inf", f"table t1 {rows}"]
    for index, scalar in enumerate(advice):
        lines.extend([f"iset i4 {index}", f"sset s6 {scalar}", "tstore t1 i4 p8 s6 s6"])
    lines.extend(
        [
            "partition i4 p7 7",
            "tload p4 s6 s7 t1 i4",
            "mulp p5 p6 s6",
            "eqp i3 p5 p7",
            "jnz i3 found",
            "sneg s6 s6",
            "mulp p5 p6 s6",
            "eqp i3 p5 p7",
            "jz i3 exhausted",
            "found:",
            "result s6",
            "halt",
            "exhausted:",
            "halt",
        ]
    )
    return "\n".join(lines) + "\n"


def _child(request):
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    return _child({"mode": "build", "scratch": str(tmp_path_factory.mktemp("generator-vm"))})


def _request(binary, tmp_path, generator="normal", **extra):
    return {
        "mode": "contract",
        "binary": binary,
        "scratch": str(tmp_path / "launch"),
        "generator": generator,
        "seed": 17,
        "bounds": {},
        "extra": extra,
    }


def _assert_prelaunch_refusal(response):
    assert response["refused"] == countedvm.GENERATOR_CONTRACT_REFUSAL
    assert response["launched"] is False
    assert response["calls"] == []


@pytest.mark.parametrize("generator", ["normal", "keyword", "kwargs", "optional"])
def test_conforming_generators_launch_exact_text_and_recover_a_verified_answer(binary, tmp_path, generator):
    response = _child(_request(binary, tmp_path, generator))
    program = programs.bsgs_program(INSTANCE.n, seed=17)
    assert response["run"]["outcome"]["result"] == 2
    assert response["run"]["program_digest"] == countedvm.blob_hash(program.encode("utf-8"))
    assert response["verification"] == [0, "OK\n", ""]
    assert response["calls"] == [{"n": INSTANCE.n, "seed": 17, "bounds": {}}]


@pytest.mark.parametrize("field", ["p", "a", "b", "P", "Q", "other"])
def test_a_generator_requiring_an_extra_argument_is_refused_before_it_or_the_vm_runs(binary, tmp_path, field):
    _assert_prelaunch_refusal(_child(_request(binary, tmp_path, f"required:{field}")))


@pytest.mark.parametrize("field", ["p", "a", "b", "P", "Q"])
def test_explicit_curve_fields_are_refused_before_the_generator_or_the_vm_runs(binary, tmp_path, field):
    _assert_prelaunch_refusal(_child(_request(binary, tmp_path, **{field: getattr(INSTANCE, field)})))


def test_an_explicit_order_override_is_refused_before_the_generator_or_the_vm_runs(binary, tmp_path):
    _assert_prelaunch_refusal(_child(_request(binary, tmp_path, n=123)))


@pytest.mark.parametrize("field", ["p", "a", "b", "P", "Q"])
def test_curve_fields_cannot_be_passed_in_the_bounds_mapping(binary, tmp_path, field):
    request = _request(binary, tmp_path)
    request["bounds"] = {field: 1}
    _assert_prelaunch_refusal(_child(request))


def test_positional_only_contract_parameters_are_refused_before_the_generator_or_vm_runs(binary, tmp_path):
    _assert_prelaunch_refusal(_child(_request(binary, tmp_path, "positional")))


@pytest.mark.parametrize("bounds", [None, [], {"cap": True}, {"cap": (2, 38)}])
def test_noninteger_or_unnamed_bounds_are_refused_before_execution(binary, tmp_path, bounds):
    request = _request(binary, tmp_path)
    request["bounds"] = bounds
    _assert_prelaunch_refusal(_child(request))


def test_nonstring_bound_names_are_refused_before_execution(binary, tmp_path):
    request = _request(binary, tmp_path)
    request["nonstring_bound_name"] = True
    _assert_prelaunch_refusal(_child(request))


def test_hidden_curve_fields_in_a_dict_subclass_are_refused_before_execution(binary, tmp_path):
    request = _request(binary, tmp_path)
    request["hidden_curve_bounds"] = True
    _assert_prelaunch_refusal(_child(request))


def test_zero_bounds_are_passed_as_supplied_without_a_cap_policy(binary, tmp_path):
    request = _request(binary, tmp_path)
    request["bounds"] = {"max_outer": 0}
    response = _child(request)
    assert response["calls"] == [{"n": INSTANCE.n, "seed": 17, "bounds": {"max_outer": 0}}]
    assert response["run"]["outcome"]["result"] == 2


def test_a_nontext_generator_result_is_refused_before_launch(binary, tmp_path):
    response = _child(_request(binary, tmp_path, "bad-result"))
    assert response["refused"] == countedvm.GENERATOR_CONTRACT_REFUSAL
    assert response["launched"] is False
    assert response["calls"] == [True]


def test_the_adapted_r6_curve_specific_advice_construction_produces_a_verified_executable_program(binary, tmp_path):
    request = _request(binary, tmp_path, "advice")
    request["mode"] = "direct-advice"
    request["bounds"] = {"rows": 128}
    request["extra"] = {field: getattr(INSTANCE, field) for field in ("p", "a", "b", "P")}
    response = _child(request)
    assert response["launched"] is True
    assert response["run"]["outcome"]["result"] == 2
    assert response["verification"] == [0, "OK\n", ""]


def test_the_contract_refuses_adapted_r6_advice_with_its_required_curve_arguments(binary, tmp_path):
    request = _request(binary, tmp_path, "advice")
    request["bounds"] = {"rows": 128}
    _assert_prelaunch_refusal(_child(request))


def test_the_contract_refuses_adapted_r6_advice_even_with_all_curve_arguments_supplied(binary, tmp_path):
    request = _request(binary, tmp_path, "advice")
    request["bounds"] = {"rows": 128}
    request["extra"] = {field: getattr(INSTANCE, field) for field in ("p", "a", "b", "P")}
    response = _child(request)
    assert response.get("launched") is False, response
    _assert_prelaunch_refusal(response)


def _child_main():
    request = json.loads(sys.stdin.read())
    if request["mode"] == "build":
        binary = countedvm.build(scratch=request["scratch"])
        print(json.dumps({"path": str(binary), "digest": countedvm.file_digest(binary)}))
        return
    choices = {
        "normal": _generator,
        "keyword": _keyword_generator,
        "kwargs": _kwargs_generator,
        "optional": _optional_generator,
        "positional": _positional_generator,
        "bad-result": _bad_result_generator,
        "advice": _r6_advice_generator,
        "required:p": _requires_p,
        "required:a": _requires_a,
        "required:b": _requires_b,
        "required:P": _requires_P,
        "required:Q": _requires_Q,
        "required:other": _requires_other,
    }
    name = request["generator"]
    generator = choices[name]
    binary = request["binary"]
    scratch = Path(request["scratch"])
    if request.get("nonstring_bound_name"):
        request["bounds"] = {3: 4}
    if request.get("hidden_curve_bounds"):
        request["bounds"] = _HiddenCurveBounds(p=INSTANCE.p)
    try:
        if request["mode"] == "direct-advice":
            program = _r6_advice_generator(
                n=INSTANCE.n,
                seed=request["seed"],
                bounds=request["bounds"],
                **request["extra"],
            )
            run = countedvm.launch(
                binary["path"],
                binary["digest"],
                INSTANCE,
                program,
                BUDGET,
                attempt_id="generator-contract",
                scratch_dir=scratch,
            )
        else:
            run = countedvm.generate_and_launch(
                binary["path"],
                binary["digest"],
                INSTANCE,
                generator,
                BUDGET,
                seed=request["seed"],
                bounds=request["bounds"],
                attempt_id="generator-contract",
                scratch_dir=scratch,
                **request["extra"],
            )
        result = run.outcome.result
        assert INSTANCE.P is not None and INSTANCE.Q is not None
        fields = (INSTANCE.p, INSTANCE.a, INSTANCE.b, INSTANCE.n, *INSTANCE.P, *INSTANCE.Q, result)
        verified = pari.run_gp([str(verifier.SCRIPT_PATH)], verifier.render_line(fields))
        response = {"run": dataclasses.asdict(run), "verification": verified}
    except countedvm.LaunchRefused as exc:
        response = {"refused": exc.reason}
    response.update({"launched": (scratch / "stdout").is_file(), "calls": CALLS})
    print(json.dumps(response))


if __name__ == "__main__":
    _child_main()
