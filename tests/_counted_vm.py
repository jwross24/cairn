import json
import subprocess
import sys

from cairn import countedvm
from cairn.countedvm import Instance
from cairn.pari import pari

REPO_ROOT = countedvm.REPO_ROOT
P_FIELD = 23
A = 1
B = 1
N = 28
POINTS = [None] + [
    (x, y) for x in range(P_FIELD) for y in range(P_FIELD) if (y * y - (x**3 + A * x + B)) % P_FIELD == 0
]
CURVE = pari.ellinit([0, 0, 0, A, B], P_FIELD)
BUDGET = 10_000


def run_text(tmp_path, text):
    file = tmp_path / "input.txt"
    file.write_text(text)
    completed = subprocess.run(
        [sys.executable, "-m", "cairn.countedvm", "--input", str(file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    assert completed.stderr == ""
    return countedvm.decode(completed.stdout, completed.returncode)


def run(tmp_path, instance, program, budget, *, instruction_set="plain/1"):
    return run_text(tmp_path, countedvm.document(instance, program, budget, instruction_set=instruction_set))


BATCH_CHILD = """
import json
import subprocess
import sys
from cairn import countedvm
binary = str(countedvm.cached_binary())
results = []
for text in json.loads(sys.stdin.read()):
    completed = subprocess.run(
        [binary], input=text, capture_output=True, text=True, timeout=countedvm.RUN_TIMEOUT_S, check=False
    )
    results.append([completed.stdout, completed.stderr, completed.returncode])
print(json.dumps(results))
"""


def run_batch(documents):
    completed = subprocess.run(
        [sys.executable, "-c", BATCH_CHILD],
        input=json.dumps(documents),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    results = json.loads(completed.stdout)
    assert len(results) == len(documents)
    outcomes = []
    for stdout, stderr, exit_code in results:
        assert stderr == ""
        outcomes.append(countedvm.decode(stdout, exit_code))
    return outcomes


def pari_point(point):
    if point is None:
        return pari([0])
    return pari([point[0], point[1]])


def lift(point):
    if len(point) == 1:
        return None
    return (int(point[0].lift()), int(point[1].lift()))


def make_instance(point_p=None, point_q=None):
    return Instance(P_FIELD, A, B, N, point_p, point_q)


def inf_or_text(point):
    return "inf" if point is None else f"{point[0]} {point[1]}"
