import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _ci_lanes import CI_LANES
from ci_gate import declared_lanes, green_run, main, missing_lanes

SHA = "53ee1368af47cd9aa023b33dd3997f899771d984"
LANES_SOURCE = "    strategy:\n      matrix:\n        lane: [python, lean-core]\n"


def done(stdout="", rc=0, stderr=""):
    return subprocess.CompletedProcess([], rc, stdout, stderr)


class FakeWorld:
    def __init__(self, *, pushed=True, runs=None, jobs=None, lanes=LANES_SOURCE, br_rc=0, gh_rc=0):
        self.pushed = pushed
        self.runs = runs if runs is not None else [{"databaseId": 7, "status": "completed", "conclusion": "success"}]
        self.jobs = (
            jobs
            if jobs is not None
            else [
                {"name": "check (python)", "conclusion": "success"},
                {"name": "check (lean-core)", "conclusion": "success"},
            ]
        )
        self.lanes = lanes
        self.br_rc = br_rc
        self.gh_rc = gh_rc
        self.calls = []

    def __call__(self, cmd):
        cmd = list(cmd)
        self.calls.append(cmd)
        if cmd[:2] == ["git", "rev-parse"]:
            return done(SHA + "\n")
        if cmd[:3] == ["git", "branch", "-r"]:
            return done("  origin/main\n" if self.pushed else "")
        if cmd[:2] == ["git", "show"]:
            return done(self.lanes)
        if cmd[:3] == ["gh", "run", "list"]:
            return done(json.dumps(self.runs), self.gh_rc, "gh: auth" if self.gh_rc else "")
        if cmd[:3] == ["gh", "run", "view"]:
            return done(json.dumps({"jobs": self.jobs}))
        if cmd[1:3] == ["gate", "report"]:
            return done("", self.br_rc, "br refused" if self.br_rc else "")
        raise AssertionError(f"unexpected command {cmd}")

    def reported(self):
        return [c for c in self.calls if c[1:3] == ["gate", "report"]]


def test_a_green_run_covering_every_declared_lane_records_the_gate(tmp_path):
    world = FakeWorld()
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 0
    (report,) = world.reported()
    assert report[report.index("--status") + 1] == "pass"
    assert report[report.index("--provider") + 1] == "ci"
    assert f"sha {SHA}" in report[report.index("--note") + 1]
    assert (
        "GATE_REPORT bead=cairn-x gate=check status=pass exit=0 provider=ci run=7"
        in (tmp_path / ".check.log").read_text()
    )


def test_a_commit_on_no_remote_branch_records_nothing(tmp_path):
    world = FakeWorld(pushed=False)
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 1
    assert world.reported() == []
    assert "reason=ci-not-pushed" in (tmp_path / ".check.log").read_text()


def test_a_run_still_in_progress_or_failed_records_nothing(tmp_path):
    for runs in (
        [{"databaseId": 8, "status": "in_progress", "conclusion": ""}],
        [{"databaseId": 9, "status": "completed", "conclusion": "failure"}],
        [{"databaseId": 10, "status": "completed", "conclusion": "timed_out"}],
        [],
    ):
        world = FakeWorld(runs=runs)
        assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 1, runs
        assert world.reported() == [], runs
    assert "reason=ci-not-green" in (tmp_path / ".check.log").read_text()


def test_a_declared_lane_with_no_successful_job_records_nothing(tmp_path):
    jobs = [{"name": "check (python)", "conclusion": "success"}, {"name": "check (lean-core)", "conclusion": "skipped"}]
    world = FakeWorld(jobs=jobs)
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 1
    assert world.reported() == []
    assert "reason=ci-lane-missing run=7 lanes=lean-core" in (tmp_path / ".check.log").read_text()


def test_lanes_are_read_from_the_verified_commit_not_the_working_tree(tmp_path):
    world = FakeWorld(lanes="        lane: [python]\n        lane: [lean-core, added-later]\n")
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 1
    assert ["git", "show", f"{SHA}:.github/workflows/ci.yml"] in world.calls
    assert world.reported() == []


def test_gh_failing_is_unanswered_not_a_pass(tmp_path):
    world = FakeWorld(gh_rc=4)
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 3
    assert world.reported() == []
    assert "reason=ci-unanswered" in (tmp_path / ".check.log").read_text()


def test_br_refusing_the_report_is_an_error_exit(tmp_path):
    world = FakeWorld(br_rc=1)
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 3


def test_a_missing_bead_argument_is_a_usage_error(tmp_path):
    assert main([], run=FakeWorld(), root=tmp_path) == 2


def test_the_newest_green_run_is_chosen_and_others_are_skipped():
    runs = [
        {"databaseId": 3, "status": "completed", "conclusion": "failure"},
        {"databaseId": 2, "status": "completed", "conclusion": "success"},
        {"databaseId": 1, "status": "completed", "conclusion": "success"},
    ]
    assert green_run(runs) == 2
    assert green_run([]) is None


def test_missing_lanes_names_each_lane_without_a_successful_job():
    jobs = [{"name": "check (a)", "conclusion": "success"}, {"name": "check (b)", "conclusion": "failure"}]
    assert missing_lanes(("a", "b", "c"), jobs) == ["b", "c"]


def test_the_workflow_matrix_declares_exactly_the_registry_lanes():
    root = Path(__file__).resolve().parents[2]
    matrix = declared_lanes((root / ".github/workflows/ci.yml").read_text())
    assert sorted(matrix) == sorted(CI_LANES)


def test_a_workflow_with_no_lane_matrix_is_unanswered(tmp_path):
    world = FakeWorld(lanes="name: ci\n")
    assert main(["--bead", "cairn-x"], run=world, root=tmp_path) == 3
    assert world.reported() == []
