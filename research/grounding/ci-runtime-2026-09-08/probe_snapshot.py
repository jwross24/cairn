import argparse
import json
import runpy
import statistics
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--before", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
before = runpy.run_path(str(args.before))["_snapshot"]
after = runpy.run_path(str(root / "tests/conftest.py"))["_snapshot"]
expected = before(root)
assert after(root) == expected
samples = {"before": [], "after": []}
for _ in range(7):
    for label, function in [("before", before), ("after", after)]:
        start = time.perf_counter()
        for _ in range(50):
            assert function(root) == expected
        samples[label].append((time.perf_counter() - start) / 50)
print(
    json.dumps(
        {
            "files": len(expected),
            "samples": samples,
            "median_seconds": {key: statistics.median(value) for key, value in samples.items()},
        },
        indent=2,
    )
)
