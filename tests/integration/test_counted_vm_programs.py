import hashlib
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import countedvm
from cairn.countedvm import programs

CHILD = Path(__file__).resolve().parents[1] / "fixtures" / "countedvm_programs_child.py"
CORPUS = countedvm.REPO_ROOT / "src" / "cairn" / "skills" / "rho_dp_corpus.json"
BUDGET = 10_000_000
GENERATED_SEEDS = tuple(range(101, 111))


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


def _dp_program(n, *, seed=17, **overrides):
    outer, inner = programs.default_caps(n)
    parameters = {
        "seed": seed,
        "theta_bits": programs.default_theta(n.bit_length()),
        "max_outer": outer,
        "max_inner": inner,
        **overrides,
    }
    return programs.dp_rho_program(n, **parameters)


@pytest.fixture(scope="module")
def generated_instances():
    code = (
        "import json\n"
        "from cairn.skills import instance_maker\n"
        "rows = []\n"
        f"for bits in (28, 30):\n    for seed in {GENERATED_SEEDS!r}:\n"
        "        made = instance_maker.run(bits, seed)\n"
        "        assert made.status == instance_maker.STATUS_OK\n"
        "        rows.append([bits, seed, [made.p, made.a, made.b, made.n, list(made.P), list(made.Q)], made.x])\n"
        "print(json.dumps(rows))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=countedvm.REPO_ROOT,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return {(bits, seed): (instance, expected) for bits, seed, instance, expected in json.loads(completed.stdout)}


@pytest.mark.parametrize("case", ["F5", "GF101", "bits20_seed1"])
def test_dp_rho_recovers_corpus_answers_with_independent_verification_and_repeat_binding(genuine, tmp_path, case):
    instance, expected = _case(case)
    program = _dp_program(instance[3])
    assert program == _dp_program(instance[3])
    first = _launch(genuine, tmp_path / "first", instance, program)
    second = _launch(genuine, tmp_path / "second", instance, program)
    _assert_verified(first, expected)
    _assert_verified(second, expected)
    assert first["run"]["outcome"] == second["run"]["outcome"]
    assert first["run"]["binding"] == second["run"]["binding"]


@pytest.fixture(scope="module")
def generated_dp_runs(genuine, generated_instances, tmp_path_factory):
    root = tmp_path_factory.mktemp("dp-generated")
    runs = {}
    for (bits, seed), (instance, expected) in generated_instances.items():
        program = _dp_program(instance[3], seed=seed, theta_bits=programs.default_theta(bits))
        first = _launch(genuine, root / f"{bits}-{seed}-first", instance, program)
        second = _launch(genuine, root / f"{bits}-{seed}-second", instance, program)
        _assert_verified(first, expected)
        _assert_verified(second, expected)
        assert first["run"]["outcome"] == second["run"]["outcome"]
        assert first["run"]["binding"] == second["run"]["binding"]
        runs[bits, seed] = first
    return runs


@pytest.mark.parametrize("bits", [28, 30])
def test_dp_rho_fresh_fixed_seeds_recover_and_record_count_spread(generated_instances, generated_dp_runs, bits):
    total_ratios = []
    walk_ratios = []
    for seed in GENERATED_SEEDS:
        instance, expected = generated_instances[bits, seed]
        response = generated_dp_runs[bits, seed]
        _assert_verified(response, expected)
        count = response["run"]["outcome"]["count"]
        setup = programs.setup_ops(instance[3], seed)
        total_ratios.append(count / math.sqrt(instance[3]))
        walk_ratios.append((count - setup) / math.sqrt(instance[3]))
    print(
        json.dumps(
            {
                "bits": bits,
                "seeds": GENERATED_SEEDS,
                "launches": len(GENERATED_SEEDS),
                "answerless": sum(
                    generated_dp_runs[bits, seed]["run"]["outcome"]["result"] is None for seed in GENERATED_SEEDS
                ),
                "total_mean": statistics.mean(total_ratios),
                "total_se": statistics.stdev(total_ratios) / math.sqrt(len(total_ratios)),
                "walk_mean": statistics.mean(walk_ratios),
                "walk_se": statistics.stdev(walk_ratios) / math.sqrt(len(walk_ratios)),
            },
            sort_keys=True,
        )
    )


@pytest.mark.parametrize("inner", [65_536, 257])
def test_dp_rho_count_and_executed_follow_the_closed_forms(
    genuine, tmp_path, generated_instances, generated_dp_runs, inner
):
    bits, seed, partition_bits = 28, 101, 5
    instance, expected = generated_instances[bits, seed]
    n = instance[3]
    outer = (8 * (math.isqrt(n) + 1) + inner - 1) // inner
    program = _dp_program(n, seed=seed, max_outer=outer, max_inner=inner)
    response = (
        generated_dp_runs[bits, seed] if inner == 65_536 else _launch(genuine, tmp_path / "nested", instance, program)
    )
    _assert_verified(response, expected)
    setup = _launch(genuine, tmp_path / "setup", instance, _dp_program(n, seed=seed, max_outer=0))
    setup_outcome = setup["run"]["outcome"]
    assert setup_outcome["status"] == countedvm.STATUS_OK
    assert setup_outcome["result"] is None
    assert setup["verification"] is None
    assert setup_outcome["count"] == programs.setup_ops(n, seed, partition_bits)
    r = 1 << partition_bits
    assert setup_outcome["executed"] == 7 * r + 19
    walk_counter = program.replace("inner:\n", "inner:\niadd i8 i8 1\n").replace(
        "solve s9 s0 s2 s1 s3", "iadd i0 i8 0\nsolve s9 s0 s2 s1 s3"
    )
    counted = _launch(genuine, tmp_path / "walk-counter", instance, walk_counter)
    _assert_verified(counted, expected)
    walk = counted["run"]["outcome"]["i0"]
    outcome = response["run"]["outcome"]
    assert outcome["count"] - setup_outcome["count"] == walk
    assert counted["run"]["outcome"]["count"] == outcome["count"]
    assert counted["run"]["outcome"]["executed"] == outcome["executed"] + walk + 1
    hit_counter = program.replace("solve s9 s0 s2 s1 s3", "iadd i0 i3 1\nsolve s9 s0 s2 s1 s3")
    hit = _launch(genuine, tmp_path / "hit-counter", instance, hit_counter)
    _assert_verified(hit, expected)
    assert hit["run"]["outcome"]["executed"] == outcome["executed"] + 1
    hit_row_one_based = hit["run"]["outcome"]["i0"]
    stored = outcome["i0"]
    rows = programs.default_table_rows(n, programs.default_theta(bits))
    completed_inner_blocks = (walk - 1) // inner
    executed = 7 * r + 26 + 9 * walk + stored * (rows + 7) + hit_row_one_based + 3 * completed_inner_blocks
    assert outcome["executed"] == executed
    print(
        json.dumps(
            {
                "n": n,
                "seed": seed,
                "setup": setup_outcome["count"],
                "walk": walk,
                "count": outcome["count"],
                "stored": stored,
                "rows": rows,
                "hit_row_one_based": hit_row_one_based,
                "completed_inner_blocks": completed_inner_blocks,
                "executed": executed,
            },
            sort_keys=True,
        )
    )


def test_paired_28_bit_floyd_and_dp_rho_counts_pin_the_baseline_gap(
    genuine, tmp_path, generated_instances, generated_dp_runs
):
    floyd_counts = []
    dp_counts = []
    floyd_ratios = []
    dp_ratios = []
    for seed in GENERATED_SEEDS:
        instance, expected = generated_instances[28, seed]
        response = _launch(genuine, tmp_path / str(seed), instance, programs.rho_program(instance[3], seed=seed))
        _assert_verified(response, expected)
        floyd_counts.append(response["run"]["outcome"]["count"])
        dp_counts.append(generated_dp_runs[28, seed]["run"]["outcome"]["count"])
        floyd_ratios.append(floyd_counts[-1] / math.sqrt(instance[3]))
        dp_ratios.append(dp_counts[-1] / math.sqrt(instance[3]))
    assert floyd_counts == [31879, 25782, 41627, 7620, 63097, 119232, 54825, 24927, 24083, 74412]
    assert dp_counts == [14781, 11432, 16390, 4417, 28893, 43310, 34646, 16329, 13225, 27926]
    floyd_mean = statistics.mean(floyd_ratios)
    dp_mean = statistics.mean(dp_ratios)
    assert floyd_mean == pytest.approx(3.316121507998016, rel=1e-12)
    assert dp_mean == pytest.approx(1.490777137361223, rel=1e-12)
    assert floyd_mean > 2.2 * dp_mean
    print(
        json.dumps(
            {
                "seeds": GENERATED_SEEDS,
                "floyd_mean": floyd_mean,
                "dp_mean": dp_mean,
                "factor": floyd_mean / dp_mean,
                "minimum_factor": 2.2,
            },
            sort_keys=True,
        )
    )


@pytest.mark.parametrize(
    ("needle", "replacement"),
    [
        ("sadd s0 s0 s4\nsadd s1 s1 s5", "sadd s0 s0 s5\nsadd s1 s1 s4"),
        ("isub i3 i3 1", "iadd i3 i3 0"),
    ],
    ids=["swapped-coefficients", "wrong-dp-row"],
)
def test_dp_rho_mutants_return_ok_wrong_answers_rejected_by_independent_gp(
    genuine, tmp_path, generated_instances, needle, replacement
):
    instance, expected = generated_instances[28, 101]
    program = _dp_program(instance[3], seed=101)
    assert program.count(needle) == 1
    response = _launch(genuine, tmp_path, instance, program.replace(needle, replacement))
    outcome = response["run"]["outcome"]
    assert outcome["status"] == countedvm.STATUS_OK
    assert outcome["result"] is not None
    assert outcome["result"] != expected
    assert response["verification"]["accepted"] is False
    assert response["verification"]["reason"] == "xP-ne-Q"
    assert response["verification"]["rc"] == 1


@pytest.mark.parametrize("exit_case", ["exhausted", "full", "useless"])
def test_dp_rho_unsuccessful_exits_halt_without_a_result(genuine, tmp_path, exit_case):
    instance, _ = _case("F5" if exit_case == "useless" else "bits20_seed1")
    overrides = {"max_outer": 1, "max_inner": 1} if exit_case == "exhausted" else {}
    if exit_case == "full":
        overrides["table_rows"] = 1
    if exit_case == "useless":
        overrides = {"seed": 1, "theta_bits": 1, "max_outer": 1, "max_inner": 100}
    response = _launch(genuine, tmp_path, instance, _dp_program(instance[3], **overrides))
    outcome = response["run"]["outcome"]
    assert outcome["status"] == countedvm.STATUS_OK
    assert outcome["result"] is None
    assert response["verification"] is None
    if exit_case == "exhausted":
        assert outcome["count"] == programs.setup_ops(instance[3], 17) + 1
    if exit_case == "full":
        assert outcome["i0"] == 1
        outer, inner = programs.default_caps(instance[3])
        assert outcome["count"] - programs.setup_ops(instance[3], 17) < outer * inner
    if exit_case == "useless":
        assert outcome["i0"] == programs.MAX_INDEX


def test_dp_rho_instruction_budget_exhaustion_has_no_result(genuine, tmp_path):
    instance, _ = _case("GF101")
    response = _launch(genuine, tmp_path, instance, _dp_program(instance[3]), budget=20)
    assert response["run"]["outcome"]["status"] == countedvm.STATUS_REFUSED
    assert response["run"]["outcome"]["reason"] == "budget_exhausted"
    assert response["run"]["outcome"]["result"] is None
    assert response["verification"] is None


@pytest.mark.parametrize("point", ["P", "Q"])
def test_dp_rho_infinity_input_has_an_honest_outcome(genuine, tmp_path, point):
    instance, _ = _case("GF101")
    instance[4 if point == "P" else 5] = None
    response = _launch(genuine, tmp_path, instance, _dp_program(instance[3]))
    if point == "Q":
        _assert_verified(response, 0)
    else:
        assert response["run"]["outcome"]["status"] == countedvm.STATUS_OK
        assert response["run"]["outcome"]["result"] is None
        assert response["verification"] is None


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("seed", True),
        ("theta_bits", 0),
        ("theta_bits", 21),
        ("partition_bits", 0),
        ("partition_bits", 8),
        ("max_outer", -1),
        ("max_outer", programs.MAX_INDEX + 1),
        ("max_inner", 0),
        ("max_inner", programs.MAX_INDEX + 1),
        ("table_rows", 0),
        ("table_rows", programs.MAX_TABLE),
    ],
)
def test_dp_rho_generator_refuses_unsupported_argument_bounds(name, value):
    with pytest.raises(ValueError, match=name):
        _dp_program(89, **{name: value})


def test_dp_rho_helpers_and_program_line_limit_refuse_unsupported_sizes(monkeypatch):
    assert {"rho", "bsgs", "dp_rho"} <= programs.ALGORITHMS.keys()
    assert programs.default_theta(3) == 1
    assert programs.default_theta(28) == 6
    assert programs.default_theta(30) == 7
    assert programs.default_theta(62) == 20
    assert programs.default_table_rows(89, 1) == 96
    outer, inner = programs.default_caps(89)
    assert inner == 65_536
    assert 8 * (math.isqrt(89) + 1) <= outer * inner < 8 * (math.isqrt(89) + 1) + inner
    for n in (True, 1, programs.MAX_ORDER + 1):
        with pytest.raises(ValueError, match="n"):
            _dp_program(n)
        with pytest.raises(ValueError, match="n"):
            programs.setup_ops(n, 17)
    with pytest.raises(ValueError, match="table_rows"):
        _dp_program(programs.MAX_ORDER, theta_bits=1)
    assert len(_dp_program(89, partition_bits=programs.MAX_DP_PARTITION_BITS).splitlines()) < 4000
    monkeypatch.setattr(programs, "MAX_DP_PARTITION_BITS", 10)
    with pytest.raises(ValueError, match="fewer than 4000"):
        _dp_program(89, partition_bits=10)
