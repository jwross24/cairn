# CI lane dispatch branch-to-contract audit

## Source identity

The dispatch probe used an isolated snapshot at `133f23aa647f42eb00e9aa1063b798ad3ac606b3` plus the `db_snapshot` overlay. For `scripts/check.sh`, `tests/hook_contract/test_ci_lane_dispatch.py`, and `tests/_ci_lanes.py`, the source diff to `2de797830071146bc4433983e8ff8e5d3f90bebe` is empty. Their Git blob IDs at both revisions are respectively `b64f7345630a58535cf05972031dc54585231c41`, `214c030fb66bf2f096f5e1ce970749c02364683e`, and `cae63d4a3aae293c3a2baba27fe397ff2a5cf627`.

## Branch-to-contract map

| Branch | Existing named contract | Coverage boundary |
|---|---|---|
| Manifest validation and lane routing in `tests/_ci_lanes.py:55-138` | `test_invalid_manifests_refuse`, `test_a_stale_manifest_stops_collection`, and `test_a_test_assigned_to_two_lanes_stops_collection`; lane-population and disjoint-union contracts; hook contracts for real-repository collection and sole container ownership, including missing-Docker refusal. | The outside-root, directory, and non-container-lane early returns are not isolated as distinct cases. |
| Shell lane selection and scope planning in `scripts/check.sh:43-67,132-168` | `test_lane_dispatch_preserves_pytest_arguments` and `test_invalid_lane_selection_runs_no_gates`; gate-scope unit and hook contracts cover empty plans and staged-path forwarding. | No direct `check.sh` contract was found for the generic unknown-argument branch, every `all:*` combination, or `--bead` reporting, bypass, and missing-tool branches. |
| Gate result and final trace in `scripts/check.sh:118-130,176-205` | `test_a_failed_lane_refuses_the_gate` checks fake pytest exit 1. The measured probe below supplies shell observations for pytest exits 0, 1, 5, and 124. | The probe uses fake `uv`; it is evidence about shell exit handling, not the real test or deadline mechanisms. |
| Session deadline and backstop | `tests/integration/test_session_deadline.py:147-229` has subprocess contracts for a deadline kill and thread profile, failure-then-hang, GIL-starvation backstop, clean finish, malformed deadline refusal, valid execution, and named bypass. | These are existing plugin integration contracts. The fake-`uv` probe did not execute them or a watchdog timeout. |

The hook dispatch fixture copies `scripts/check.sh`, stubs `theater-patterns.sh`, and places a fake `uv` first on `PATH`. Each measured case issued exactly one `pytest -q --durations=25 --cairn-ci-lane=python` command. Exit 0 produced `gate_exit=0` and `RESULT pass`; exits 1, 5, and 124 each produced `gate_exit=1`, `FAIL tests`, and `RESULT fail: tests`.

## Reproduction form

The measured call loads the pytest fixture directly and sets the fake pytest subprocess exit code. This command reconstructs the four shell observations; it does not run the real pytest suite.

```bash
cd /tmp/cairn-day-lane3.uMzz8z/db-fixed
PYTHONPATH=/tmp/cairn-day-lane3.uMzz8z/db-fixed/tests:/tmp/cairn-day-lane3.uMzz8z/db-fixed/src \
uv run --no-project /Users/jwross/Documents/cairn/.venv/bin/python - <<'PY'
import json
import runpy
import tempfile
from pathlib import Path

fixture = runpy.run_path("tests/hook_contract/test_ci_lane_dispatch.py")
for pytest_exit in (0, 1, 5, 124):
    scratch = Path(tempfile.mkdtemp(prefix="cairn-dispatch-audit-"))
    run = fixture["dispatch"].__wrapped__(scratch)
    result, calls = run("--ci-lane", "python", pytest_exit=pytest_exit)
    trace = (scratch / ".check.log").read_text().splitlines()
    expected_gate_exit = 0 if pytest_exit == 0 else 1
    expected_gate_trace = "PASS tests" if pytest_exit == 0 else "FAIL tests"
    expected_result_trace = (
        "RESULT pass (fast=0 unit=0 scoped=0 lane=python)"
        if pytest_exit == 0
        else "RESULT fail: tests"
    )
    pytest_calls = [call for call in calls if "pytest" in call]
    assert result.returncode == expected_gate_exit
    assert any(line.endswith(expected_gate_trace) for line in trace)
    assert any(line.endswith(expected_result_trace) for line in trace)
    assert len(pytest_calls) == 1
    print(json.dumps({
        "pytest_exit": pytest_exit,
        "gate_exit": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "trace": trace,
        "calls": calls,
        "scratch": str(scratch),
    }))
PY
```

## No-claim

The four observations establish fake-child exit handling in the shell dispatcher only. They do not demonstrate a real watchdog timeout, the real test suite, CI deadline coverage, Lean or PARI authority, or completion of the global test-architecture audit. The exact measured receipt follows.

<details>
<summary>Exact dispatch-exit-audit.json receipt</summary>

```json
[
  {
    "pytest_exit": 0,
    "gate_exit": 0,
    "stdout": "[check] run format\n[check] pass format\n[check] run lint\n[check] pass lint\n[check] run spelling\n[check] pass spelling\n[check] run types\n[check] pass types\n[check] run theater\n[check] pass theater\n[check] run tests\n[check] pass tests\n[check] all gates pass\n",
    "stderr": "",
    "trace": "2026-09-29T16:20:45Z RUN format\n2026-09-29T16:20:45Z PASS format\n2026-09-29T16:20:45Z RUN lint\n2026-09-29T16:20:45Z PASS lint\n2026-09-29T16:20:45Z RUN spelling\n2026-09-29T16:20:45Z PASS spelling\n2026-09-29T16:20:45Z RUN types\n2026-09-29T16:20:45Z PASS types\n2026-09-29T16:20:45Z RUN theater\n2026-09-29T16:20:45Z PASS theater\n2026-09-29T16:20:45Z DEADLINE 3000s session (dumps every thread; a kill prints 'Timeout (' on stderr, and the watchdog exits 124, its faulthandler backstop 15s later exits 1; an in-process libpari call past cairn.pari.CALL_BOUND_S prints 'libpari stall in <test>' and also exits 124)\n2026-09-29T16:20:45Z RUN tests\n2026-09-29T16:20:45Z PASS tests\n2026-09-29T16:20:45Z RESULT pass (fast=0 unit=0 scoped=0 lane=python)\n",
    "calls": [
      [
        "run",
        "ruff",
        "format",
        "--check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "ruff",
        "check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "codespell"
      ],
      [
        "run",
        "ty",
        "check",
        "--python-platform",
        "darwin",
        "src",
        "tests"
      ],
      [
        "run",
        "pytest",
        "-q",
        "--durations=25",
        "--cairn-ci-lane=python"
      ]
    ],
    "scratch": "/var/folders/wp/7c8dr9tn5t3fdj8wy07zrn4w0000gn/T/cairn-dispatch-audit-xm5ejzl6"
  },
  {
    "pytest_exit": 1,
    "gate_exit": 1,
    "stdout": "[check] run format\n[check] pass format\n[check] run lint\n[check] pass lint\n[check] run spelling\n[check] pass spelling\n[check] run types\n[check] pass types\n[check] run theater\n[check] pass theater\n[check] run tests\n",
    "stderr": "[check] FAIL tests\n\n[check] FAILED: tests\n        fix formatting: uv run ruff format src tests scripts\n        fix lint:       uv run ruff check --fix src tests scripts\n        bypass (logged): CAIRN_CHECK_SKIP='<reason>' scripts/check.sh\n",
    "trace": "2026-09-29T16:20:46Z RUN format\n2026-09-29T16:20:46Z PASS format\n2026-09-29T16:20:46Z RUN lint\n2026-09-29T16:20:46Z PASS lint\n2026-09-29T16:20:46Z RUN spelling\n2026-09-29T16:20:46Z PASS spelling\n2026-09-29T16:20:46Z RUN types\n2026-09-29T16:20:46Z PASS types\n2026-09-29T16:20:46Z RUN theater\n2026-09-29T16:20:46Z PASS theater\n2026-09-29T16:20:46Z DEADLINE 3000s session (dumps every thread; a kill prints 'Timeout (' on stderr, and the watchdog exits 124, its faulthandler backstop 15s later exits 1; an in-process libpari call past cairn.pari.CALL_BOUND_S prints 'libpari stall in <test>' and also exits 124)\n2026-09-29T16:20:46Z RUN tests\n2026-09-29T16:20:46Z FAIL tests\n2026-09-29T16:20:46Z RESULT fail: tests\n",
    "calls": [
      [
        "run",
        "ruff",
        "format",
        "--check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "ruff",
        "check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "codespell"
      ],
      [
        "run",
        "ty",
        "check",
        "--python-platform",
        "darwin",
        "src",
        "tests"
      ],
      [
        "run",
        "pytest",
        "-q",
        "--durations=25",
        "--cairn-ci-lane=python"
      ]
    ],
    "scratch": "/var/folders/wp/7c8dr9tn5t3fdj8wy07zrn4w0000gn/T/cairn-dispatch-audit-x5evz9ww"
  },
  {
    "pytest_exit": 5,
    "gate_exit": 1,
    "stdout": "[check] run format\n[check] pass format\n[check] run lint\n[check] pass lint\n[check] run spelling\n[check] pass spelling\n[check] run types\n[check] pass types\n[check] run theater\n[check] pass theater\n[check] run tests\n",
    "stderr": "[check] FAIL tests\n\n[check] FAILED: tests\n        fix formatting: uv run ruff format src tests scripts\n        fix lint:       uv run ruff check --fix src tests scripts\n        bypass (logged): CAIRN_CHECK_SKIP='<reason>' scripts/check.sh\n",
    "trace": "2026-09-29T16:20:46Z RUN format\n2026-09-29T16:20:46Z PASS format\n2026-09-29T16:20:46Z RUN lint\n2026-09-29T16:20:46Z PASS lint\n2026-09-29T16:20:46Z RUN spelling\n2026-09-29T16:20:46Z PASS spelling\n2026-09-29T16:20:46Z RUN types\n2026-09-29T16:20:46Z PASS types\n2026-09-29T16:20:46Z RUN theater\n2026-09-29T16:20:46Z PASS theater\n2026-09-29T16:20:46Z DEADLINE 3000s session (dumps every thread; a kill prints 'Timeout (' on stderr, and the watchdog exits 124, its faulthandler backstop 15s later exits 1; an in-process libpari call past cairn.pari.CALL_BOUND_S prints 'libpari stall in <test>' and also exits 124)\n2026-09-29T16:20:46Z RUN tests\n2026-09-29T16:20:46Z FAIL tests\n2026-09-29T16:20:46Z RESULT fail: tests\n",
    "calls": [
      [
        "run",
        "ruff",
        "format",
        "--check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "ruff",
        "check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "codespell"
      ],
      [
        "run",
        "ty",
        "check",
        "--python-platform",
        "darwin",
        "src",
        "tests"
      ],
      [
        "run",
        "pytest",
        "-q",
        "--durations=25",
        "--cairn-ci-lane=python"
      ]
    ],
    "scratch": "/var/folders/wp/7c8dr9tn5t3fdj8wy07zrn4w0000gn/T/cairn-dispatch-audit-x94irzvy"
  },
  {
    "pytest_exit": 124,
    "gate_exit": 1,
    "stdout": "[check] run format\n[check] pass format\n[check] run lint\n[check] pass lint\n[check] run spelling\n[check] pass spelling\n[check] run types\n[check] pass types\n[check] run theater\n[check] pass theater\n[check] run tests\n",
    "stderr": "[check] FAIL tests\n\n[check] FAILED: tests\n        fix formatting: uv run ruff format src tests scripts\n        fix lint:       uv run ruff check --fix src tests scripts\n        bypass (logged): CAIRN_CHECK_SKIP='<reason>' scripts/check.sh\n",
    "trace": "2026-09-29T16:20:47Z RUN format\n2026-09-29T16:20:47Z PASS format\n2026-09-29T16:20:47Z RUN lint\n2026-09-29T16:20:47Z PASS lint\n2026-09-29T16:20:47Z RUN spelling\n2026-09-29T16:20:47Z PASS spelling\n2026-09-29T16:20:47Z RUN types\n2026-09-29T16:20:47Z PASS types\n2026-09-29T16:20:47Z RUN theater\n2026-09-29T16:20:47Z PASS theater\n2026-09-29T16:20:47Z DEADLINE 3000s session (dumps every thread; a kill prints 'Timeout (' on stderr, and the watchdog exits 124, its faulthandler backstop 15s later exits 1; an in-process libpari call past cairn.pari.CALL_BOUND_S prints 'libpari stall in <test>' and also exits 124)\n2026-09-29T16:20:47Z RUN tests\n2026-09-29T16:20:47Z FAIL tests\n2026-09-29T16:20:47Z RESULT fail: tests\n",
    "calls": [
      [
        "run",
        "ruff",
        "format",
        "--check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "ruff",
        "check",
        "src",
        "tests",
        "scripts"
      ],
      [
        "run",
        "codespell"
      ],
      [
        "run",
        "ty",
        "check",
        "--python-platform",
        "darwin",
        "src",
        "tests"
      ],
      [
        "run",
        "pytest",
        "-q",
        "--durations=25",
        "--cairn-ci-lane=python"
      ]
    ],
    "scratch": "/var/folders/wp/7c8dr9tn5t3fdj8wy07zrn4w0000gn/T/cairn-dispatch-audit-66y9kips"
  }
]
```

</details>
