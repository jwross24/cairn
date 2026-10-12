import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import countedvm
from cairn.countedvm import programs

CHILD = Path(__file__).resolve().parents[1] / "fixtures" / "countedvm_programs_child.py"
CORPUS = countedvm.REPO_ROOT / "src" / "cairn" / "skills" / "rho_dp_corpus.json"
BUDGET = 10_000_000


def _child(request):
    completed = subprocess.run(
        [sys.executable, str(CHILD)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=countedvm.REPO_ROOT,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.fixture(scope="module")
def genuine(tmp_path_factory):
    return _child({"op": "build", "scratch": str(tmp_path_factory.mktemp("vm-programs"))})


def _case(name):
    case = next(row for row in json.loads(CORPUS.read_text())["cases"] if row["id"] == name)
    fields = {key: row["value"] for key, row in case["fields"].items()}
    return [fields[key] for key in ("p", "a", "b", "n", "P", "Q")], fields.get("x")


def _launch(genuine, tmp_path, instance, program, *, budget=BUDGET, attempt_id="program-attempt"):
    request = {
        "op": "launch",
        "binary": genuine["binary"],
        "digest": genuine["digest"],
        "instance": instance,
        "budget": budget,
        "attempt_id": attempt_id,
        "scratch": str(tmp_path),
    }
    request["program_path" if isinstance(program, Path) else "program"] = str(program)
    return _child(request)


def _assert_verified(response, expected):
    outcome = response["run"]["outcome"]
    assert outcome["status"] == countedvm.STATUS_OK
    assert outcome["result"] == expected
    assert response["verification"] == {
        "accepted": True,
        "reason": None,
        "rc": 0,
        "stdout": "OK\n",
        "stderr": "",
    }


@pytest.mark.parametrize("case", ["F5", "GF101", "bits20_seed1"])
@pytest.mark.parametrize("algorithm", ["bsgs", "rho"])
def test_vm_algorithms_recover_nontrivial_known_answers_and_repeat_counted_results(genuine, tmp_path, case, algorithm):
    instance, expected = _case(case)
    generator = programs.bsgs_program if algorithm == "bsgs" else programs.rho_program
    program = generator(instance[3], seed=17)
    assert generator(instance[3], seed=17) == program
    first = _launch(genuine, tmp_path / "first", instance, program)
    second = _launch(genuine, tmp_path / "second", instance, program)
    _assert_verified(first, expected)
    _assert_verified(second, expected)
    assert first["run"]["outcome"] == second["run"]["outcome"]
    assert first["run"]["binding"] == second["run"]["binding"]
    assert first["run"]["argv"] == [genuine["binary"]]
    assert first["run"]["measurement_scope"] == "tree"
    assert first["run"]["outcome"]["count"] > 0


@pytest.mark.parametrize("generator", [programs.bsgs_program, programs.rho_program])
def test_infinity_target_is_verified_with_real_gp(genuine, tmp_path, generator):
    instance, _ = _case("GF101")
    instance[5] = None
    _assert_verified(_launch(genuine, tmp_path, instance, generator(instance[3])), 0)


def test_bsgs_count_includes_babies_stride_offset_and_candidate_verification(genuine, tmp_path):
    instance, expected = _case("GF101")
    program = programs.bsgs_program(instance[3], seed=expected)
    response = _launch(genuine, tmp_path, instance, program)
    _assert_verified(response, expected)
    m = math.isqrt(instance[3] - 1) + 1
    assert response["run"]["outcome"]["count"] == m + 1 + 2 * countedvm.expected_mul_ops(expected)


def test_bsgs_handles_order_two_and_a_target_outside_the_base_subgroup(genuine, tmp_path):
    instance = [23, 1, 1, 2, [4, 0], [4, 0]]
    _assert_verified(_launch(genuine, tmp_path / "order-two", instance, programs.bsgs_program(2)), 1)
    instance[5] = [3, 10]
    response = _launch(genuine, tmp_path / "outside", instance, programs.bsgs_program(2))
    assert response["run"]["outcome"]["status"] == countedvm.STATUS_OK
    assert response["run"]["outcome"]["result"] is None
    assert response["verification"] is None


@pytest.mark.parametrize("generator", [programs.bsgs_program, programs.rho_program])
def test_infinity_base_with_nonzero_target_has_no_result(genuine, tmp_path, generator):
    instance, _ = _case("GF101")
    instance[4] = None
    response = _launch(genuine, tmp_path, instance, generator(instance[3]))
    assert response["run"]["outcome"]["status"] == countedvm.STATUS_OK
    assert response["run"]["outcome"]["result"] is None


def test_a_bounded_rho_walk_exhausts_without_claiming_success(genuine, tmp_path):
    instance, _ = _case("bits20_seed1")
    program = programs.rho_program(instance[3], seed=17, max_steps=1, restarts=1)
    response = _launch(genuine, tmp_path, instance, program)
    assert response["run"]["outcome"]["status"] == countedvm.STATUS_OK
    assert response["run"]["outcome"]["result"] is None
    assert response["verification"] is None


def test_instruction_budget_exhaustion_refuses_a_rho_attempt(genuine, tmp_path):
    instance, _ = _case("GF101")
    response = _launch(genuine, tmp_path, instance, programs.rho_program(instance[3]), budget=20)
    assert response["run"]["outcome"]["status"] == countedvm.STATUS_REFUSED
    assert response["run"]["outcome"]["reason"] == "budget_exhausted"
    assert response["run"]["outcome"]["result"] is None


def test_a_fruitless_collision_restarts_and_a_noninvertible_collision_refuses(genuine, tmp_path):
    instance, expected = _case("GF101")
    program = programs.rho_program(instance[3], seed=22, max_steps=100)
    response = _launch(genuine, tmp_path / "fruitless", instance, program)
    _assert_verified(response, expected)
    assert response["run"]["outcome"]["i0"] > 0
    mutant = tmp_path / "fruitless-denominator.vm"
    assert program.count("seq i4 s1 s3") == 1
    mutant.write_text(program.replace("seq i4 s1 s3", "iset i4 0"))
    refused = _launch(genuine, tmp_path / "fruitless-mutant", instance, mutant)
    assert refused["run"]["outcome"]["status"] == countedvm.STATUS_REFUSED
    assert refused["run"]["outcome"]["reason"] == "zero_denominator"
    assert refused["run"]["outcome"]["result"] is None
    composite = [419, 1, 0, 21, [386, 8], [148, 239]]
    refused = _launch(genuine, tmp_path / "composite", composite, programs.rho_program(21, seed=0))
    assert refused["run"]["outcome"]["status"] == countedvm.STATUS_REFUSED
    assert refused["run"]["outcome"]["reason"] == "zero_denominator"
    assert refused["verification"] is None


@pytest.mark.parametrize("generator", [programs.bsgs_program, programs.rho_program])
def test_order_equal_to_field_stays_a_named_refusal(genuine, tmp_path, generator):
    instance, _ = _case("GF101")
    instance[3] = instance[0]
    refused = _launch(genuine, tmp_path, instance, generator(instance[3]))
    assert refused["run"]["outcome"]["status"] == countedvm.STATUS_REFUSED
    assert refused["run"]["outcome"]["reason"] == "order_equals_field"
    assert refused["run"]["outcome"]["result"] is None


def test_bsgs_order_one_and_rho_order_two_boundaries(genuine, tmp_path):
    zero = [23, 1, 1, 1, None, None]
    _assert_verified(_launch(genuine, tmp_path / "order-one", zero, programs.bsgs_program(1)), 0)
    order_two = [23, 1, 1, 2, [4, 0], [4, 0]]
    _assert_verified(_launch(genuine, tmp_path / "order-two", order_two, programs.rho_program(2)), 1)


def test_a_scratch_walk_coefficient_mutation_is_rejected_by_the_independent_verifier(genuine, tmp_path):
    instance, expected = _case("GF101")
    program = programs.rho_program(instance[3], seed=17)
    _assert_verified(_launch(genuine, tmp_path / "control", instance, program), expected)
    needle = "sadd s0 s0 s4"
    assert program.count(needle) == 1
    mutant = tmp_path / "mutant.vm"
    mutant.write_text(program.replace(needle, "sadd s0 s0 s5"))
    response = _launch(genuine, tmp_path / "mutant-run", instance, mutant)
    assert response["run"]["outcome"]["status"] == countedvm.STATUS_OK
    assert response["run"]["outcome"]["result"] is not None
    assert response["verification"]["accepted"] is False
    assert response["verification"]["reason"] == "xP-ne-Q"
    assert response["verification"]["rc"] == 1


def test_paired_identical_program_launches_retain_both_measurements(genuine, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("vm-aa")
    instance, expected = _case("GF101")
    program = programs.rho_program(instance[3], seed=17)
    pairs = [_launch(genuine, tmp_path / str(index), instance, program, attempt_id=f"aa-{index}") for index in range(2)]
    for response in pairs:
        _assert_verified(response, expected)
        run = response["run"]
        assert run["cpu_user_s"] + run["cpu_sys_s"] > 0
        assert run["wall_s"] > 0
        assert run["peak_rss_bytes"] > 0
        assert run["measurement_scope"] == "tree"
    assert pairs[0]["run"]["outcome"] == pairs[1]["run"]["outcome"]
    assert pairs[0]["run"]["program_digest"] == pairs[1]["run"]["program_digest"]
    assert pairs[0]["run"]["binding"] != pairs[1]["run"]["binding"]
    (tmp_path / "paired-measurements.json").write_text(json.dumps(pairs, sort_keys=True))


def test_generators_refuse_unsupported_bounds_and_do_not_take_points_or_answers():
    with pytest.raises(ValueError, match="MAX_TABLE"):
        programs.bsgs_program(programs.MAX_TABLE**2 + 1)
    for bound in (0, programs.MAX_INDEX + 1):
        with pytest.raises(ValueError, match="max_steps"):
            programs.rho_program(89, max_steps=bound)
    with pytest.raises(ValueError, match="restarts"):
        programs.rho_program(89, restarts=programs.MAX_RESTARTS + 1)
    with pytest.raises(ValueError, match="partition_bits"):
        programs.rho_program(89, partition_bits=programs.MAX_PARTITION_BITS + 1)
    for generator in (programs.bsgs_program, programs.rho_program):
        with pytest.raises(ValueError, match="n"):
            generator(True)
    assert (
        hashlib.sha256(programs.rho_program(89, seed=1).encode()).digest()
        != hashlib.sha256(programs.rho_program(89, seed=2).encode()).digest()
    )
