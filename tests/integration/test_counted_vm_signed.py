import json
import subprocess
import sys

import pytest

from cairn import countedvm, pari, verifier
from cairn.countedvm import signed_programs
from cairn.skills import instance_maker

CORPUS = countedvm.REPO_ROOT / "src" / "cairn" / "skills" / "rho_dp_corpus.json"
BUDGET = 20_000_000
CHILD = """
import dataclasses
import json
import sys
from cairn import countedvm
request = json.loads(sys.stdin.read())
if request["op"] == "build":
    result = str(countedvm.build(scratch=request["scratch"]))
else:
    fields = request["instance"]
    instance = countedvm.Instance(*fields[:4], *[None if p is None else tuple(p) for p in fields[4:]])
    result = dataclasses.asdict(countedvm.run(
        request["binary"], instance, request["program"], request["budget"],
        instruction_set=request["instruction_set"],
    ))
print(json.dumps(result))
"""


def _child(request):
    completed = subprocess.run(
        [sys.executable, "-c", CHILD],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _run(binary, instance, program, *, instruction_set="signed/1"):
    fields = [instance.p, instance.a, instance.b, instance.n, instance.P, instance.Q]
    result = _child(
        {
            "op": "run",
            "binary": binary,
            "instance": fields,
            "program": program,
            "budget": BUDGET,
            "instruction_set": instruction_set,
        }
    )
    if result["p0"] is not None:
        result["p0"] = tuple(result["p0"])
    return countedvm.Outcome(**result)


@pytest.fixture(scope="module")
def binary(tmp_path_factory):
    return _child({"op": "build", "scratch": str(tmp_path_factory.mktemp("signed-vm"))})


def _case(name):
    case = next(row for row in json.loads(CORPUS.read_text())["cases"] if row["id"] == name)
    fields = {key: row["value"] for key, row in case["fields"].items()}
    instance = countedvm.Instance(
        fields["p"],
        fields["a"],
        fields["b"],
        fields["n"],
        tuple(fields["P"]),
        tuple(fields["Q"]),
    )
    return instance, fields["x"]


def _program(n, seed=17, **bounds):
    theta = signed_programs.default_theta(n.bit_length())
    outer, inner = signed_programs.default_caps(n)
    return signed_programs.negation_dp_rho_program(
        n,
        seed=seed,
        theta_bits=theta,
        max_outer=outer,
        max_inner=inner,
        **bounds,
    )


def _verify(instance, result):
    fields = (instance.p, instance.a, instance.b, instance.n, *instance.P, *instance.Q, result)
    rc, stdout, stderr = pari.run_gp([str(verifier.SCRIPT_PATH)], verifier.render_line(fields))
    assert (rc, stdout, stderr) == (0, "OK\n", "")


@pytest.mark.parametrize("case", ["F5", "GF101", "bits20_seed1"])
def test_signed_rho_recovers_known_answers_with_an_independent_verifier(binary, case):
    instance, expected = _case(case)
    program = _program(instance.n)
    assert program == _program(instance.n)
    first = _run(binary, instance, program)
    second = _run(binary, instance, program)
    assert first == second
    assert first.status == "OK"
    assert first.instruction_set == "signed/1"
    assert first.result == expected
    _verify(instance, first.result)
    assert first.program_bytes == len(program.encode("ascii"))
    assert first.program_lines == len(program.splitlines())


@pytest.mark.parametrize("seed", [90701, 90702])
def test_signed_rho_recovers_fresh_instances_with_an_independent_verifier(binary, seed):
    made = instance_maker.run(20, seed)
    instance = countedvm.Instance(made.p, made.a, made.b, made.n, made.P, made.Q)
    outcome = _run(binary, instance, _program(instance.n, seed))
    assert outcome.status == "OK"
    assert outcome.result == made.x
    _verify(instance, outcome.result)


@pytest.mark.parametrize("steps", [0, 1, 5])
def test_each_bounded_signed_walk_transition_has_one_counted_addition(binary, steps):
    instance, _ = _case("bits20_seed1")
    program = signed_programs.negation_dp_rho_program(
        instance.n,
        seed=17,
        theta_bits=20,
        max_outer=steps,
        max_inner=1,
    )
    outcome = _run(binary, instance, program)
    assert outcome.status == "OK"
    assert outcome.result is None
    assert outcome.count == signed_programs.setup_ops(instance.n, 17) + steps


def test_the_signed_baseline_is_refused_by_the_default_instruction_set(binary):
    instance, _ = _case("GF101")
    outcome = _run(binary, instance, _program(instance.n), instruction_set="plain/1")
    assert (outcome.status, outcome.reason, outcome.count, outcome.executed) == (
        "REFUSED",
        "instruction_set_forbids_canonicalp",
        0,
        0,
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [("theta_bits", 0), ("partition_bits", 8), ("max_outer", -1), ("max_inner", 0), ("table_rows", 0)],
)
def test_signed_generator_refuses_unsupported_bounds(name, value):
    bounds = {"seed": 17, "theta_bits": 1, "max_outer": 1, "max_inner": 1, name: value}
    with pytest.raises(ValueError, match=name):
        signed_programs.negation_dp_rho_program(89, **bounds)
