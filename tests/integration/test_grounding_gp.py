import subprocess
from pathlib import Path

import pytest

from cairn import log, pari

PROBE_GP = Path(__file__).resolve().parent / "gp" / "probe.gp"
CURVE60_VECTOR = "curve60_seed1.json"
ELLCARD60 = "print(ellcard(ellinit([{a},{b}],{p})))"
STARTUP_FAIL_STDOUT = "### Errors on startup, exiting...\n\n\n"
STARTUP_FAIL_STDERR = "the PARI stack overflows !"
GP_VERSION_PREFIX = "2.17"

GP_ROWS = [
    ("64M", "1/0", 0, "", "_/_: impossible inverse in gdiv: 0"),
    ("64M", "f3(1,2)", 0, "1 2 0\n", ""),
    ("64M", "f3(1,2,3)", 0, "1 2 3\n", ""),
    ("64M", "ok()", 0, "OK\n", ""),
    ("64M", "fail()", 1, 'FAIL ["x"]\n', ""),
    ("8M", ELLCARD60, 0, "", "ellcard: the PARI stack overflows !"),
    ("64M", ELLCARD60, 0, "{n}\n", ""),
    ("2M", "ok()", 1, STARTUP_FAIL_STDOUT, STARTUP_FAIL_STDERR),
    ("1M", "ok()", 1, STARTUP_FAIL_STDOUT, STARTUP_FAIL_STDERR),
    ("3M", "ok()", 0, "OK\n", ""),
    ("64M", "print(ellinit([0,1],2))", 0, "[]\n", ""),
    ("64M", "print(ellisoncurve(ellinit([0,1],2),[0,1]))", 0, "", "ellisoncurve: incorrect type in checkell (t_VEC)"),
    ("64M", "print(ellinit([0,1],3))", 0, "[]\n", ""),
    ("64M", "print(ellisoncurve(ellinit([0,1],5),[0,1]))", 0, "1\n", ""),
]

GP_IDS = [
    "64M-div-by-zero-rc0-stderr",
    "64M-f3-two-args-zero-filled",
    "64M-f3-three-args-control",
    "64M-ok-rc0-empty-stderr",
    "64M-fail-rc1-stdout-empty-stderr",
    "8M-ellcard60-overflow-rc0-stderr",
    "64M-ellcard60-prints-n",
    "2M-startup-overflow-rc1",
    "1M-startup-overflow-rc1",
    "3M-startup-fits-ok",
    "64M-ellinit-p2-returns-empty",
    "64M-ellisoncurve-p2-fatal-rc0",
    "64M-ellinit-p3-returns-empty",
    "64M-ellisoncurve-p5-control",
]

CURVE40 = {"p": 617956103213, "a": 574238428165, "b": 529421460422}
PRNG_SEED = 1
PRNG_PREFIX_DRAWS = 2
PRNG_BASELINE_DRAW = 14991082624209354397

PRNG_ROWS = [
    (40, "ellcard", False, 14991082624209354397),
    (40, "ellsea", True, 11721172991787151380),
    (60, "ellcard", True, 12458736420605239190),
    (60, "ellsea1", True, 12458736420605239190),
]

PRNG_CALLS = {
    "ellcard": ("ellcard(E)", lambda P, E: P.ellcard(E)),
    "ellsea": ("ellsea(E)", lambda P, E: P.ellsea(E)),
    "ellsea1": ("ellsea(E,1)", lambda P, E: P.ellsea(E, 1)),
}


def _fill(template, curve60):
    return template.format(**curve60) if "{" in template else template


def test_gp_version_short_is_2_17():
    lg = log.get("grounding.gp")
    argv = [pari.GP_BIN, "--version-short"]
    proc = subprocess.run(argv, capture_output=True, text=True)
    lg.info(
        "gp_version",
        command=" ".join(argv),
        rc=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        gp_bin=pari.GP_BIN,
        versions=pari.pari_versions(),
    )
    assert proc.returncode == 0
    assert proc.stdout.startswith(GP_VERSION_PREFIX)


@pytest.mark.parametrize(
    ("stack", "stdin_line", "expected_rc", "expected_stdout", "expected_stderr_fragment"), GP_ROWS, ids=GP_IDS
)
def test_gp_exit_arity_stack_and_small_p_facts(
    load_vector, stack, stdin_line, expected_rc, expected_stdout, expected_stderr_fragment
):
    lg = log.get("grounding.gp")
    curve60 = load_vector(CURVE60_VECTOR)
    line = _fill(stdin_line, curve60)
    expected_out = _fill(expected_stdout, curve60)
    argv = [*pari.gp_argv(stack), str(PROBE_GP)]
    rc, out, err = pari.run_gp([str(PROBE_GP)], line + "\n", stack=stack)
    lg.info(
        "gp_fact",
        command=f"{' '.join(argv)} <<< {line!r}",
        argv=argv,
        stack=stack,
        stdin=line,
        rc=rc,
        stdout=out,
        stderr=err,
        gp_bin=pari.GP_BIN,
    )
    assert rc == expected_rc
    assert out == expected_out
    if expected_stderr_fragment == "":
        assert err == ""
    else:
        assert expected_stderr_fragment in err


def _curve(bits, curve60):
    if bits == 40:
        return CURVE40
    return {key: int(curve60[key]) for key in ("p", "a", "b")}


def _gp_final_draw(curve, call_expr):
    prefix = " ".join("random(2^64);" for _ in range(PRNG_PREFIX_DRAWS))
    call = f"{call_expr};" if call_expr else ""
    code = f"E=ellinit([{curve['a']},{curve['b']}],{curve['p']}); setrand({PRNG_SEED}); {prefix} {call} print(random(2^64))"
    rc, out, err = pari.run_gp([], code + "\n", stack="64M")
    assert (rc, err) == (0, "")
    return code, int(out.strip())


def _cypari2_final_draw(curve, call):
    P = pari.pari
    E = P.ellinit([curve["a"], curve["b"]], curve["p"])
    P.setrand(PRNG_SEED)
    for _ in range(PRNG_PREFIX_DRAWS):
        P.random(2**64)
    if call is not None:
        call(P, E)
    return int(P.random(2**64))


@pytest.mark.parametrize("backend", ["gp", "cypari2"])
@pytest.mark.parametrize(
    ("bits", "call_name", "state_changes", "expected_treated_draw"),
    PRNG_ROWS,
    ids=[f"{b}bit-{c}-{'consumes' if s else 'leaves'}-prng" for b, c, s, _d in PRNG_ROWS],
)
def test_prng_consumption_of_point_counting_calls(
    load_vector, bits, call_name, state_changes, expected_treated_draw, backend
):
    lg = log.get("grounding.gp")
    curve = _curve(bits, load_vector(CURVE60_VECTOR))
    gp_expr, py_call = PRNG_CALLS[call_name]
    if backend == "gp":
        base_code, baseline = _gp_final_draw(curve, "")
        code, treated = _gp_final_draw(curve, gp_expr)
        command = f"gp -q -f -s 64M <<< {code!r} vs baseline {base_code!r}"
    else:
        baseline = _cypari2_final_draw(curve, None)
        treated = _cypari2_final_draw(curve, py_call)
        command = f"cypari2: ellinit([{curve['a']},{curve['b']}],{curve['p']}); setrand({PRNG_SEED}); random(2^64) x{PRNG_PREFIX_DRAWS}; {gp_expr}; random(2^64) vs the same without {gp_expr}"
    lg.info(
        "prng_consumption",
        command=command,
        backend=backend,
        bits=bits,
        call=gp_expr,
        baseline_draw=baseline,
        treated_draw=treated,
        state_changed=baseline != treated,
        versions=pari.pari_versions(),
    )
    assert baseline == PRNG_BASELINE_DRAW
    assert treated == expected_treated_draw
    assert (baseline != treated) is state_changes
