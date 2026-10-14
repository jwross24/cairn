import json
import sys

from cairn import runner

MIB = 1024**2
ALLOCATING_CHILD = """
memory = bytearray(200 * 1024**2)
for offset in range(0, len(memory), 4096):
    memory[offset] = 1
"""


def test_child_peak_rss_tracks_allocation_from_an_inflated_parent(tmp_path):
    parent_memory = bytearray(300 * MIB)
    for offset in range(0, len(parent_memory), 4096):
        parent_memory[offset] = 1
    readings = {}
    for label, code in (("idle", "pass"), ("allocating", ALLOCATING_CHILD)):
        child_dir = tmp_path / label
        child_dir.mkdir()
        launch = runner.spawn_and_wait(
            [sys.executable, "-c", code],
            child_dir / "stdout",
            child_dir / "stderr",
            wall_cap_s=30,
            env=runner.child_env(),
        )
        assert launch.exit_status == 0, (child_dir / "stderr").read_text()
        assert not launch.timed_out
        readings[label] = launch.peak_rss_bytes
    print(json.dumps(readings, sort_keys=True))
    assert readings["allocating"] >= readings["idle"] + 150 * MIB, readings
    assert readings["idle"] < 150 * MIB, readings
