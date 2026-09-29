from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

LANES = (
    "python",
    "lean",
    "solution",
    "solution-plan-exact",
    "solution-plan-refusals",
    "container",
    "container-replay-exact",
    "container-replay-refusals",
)
RUNS = {
    "baseline": {
        "sha": "5882af8d500e325da3a854606a2b49cdc38c14cc",
        "url": "https://github.com/jwross24/cairn/actions/runs/35704472553",
        "json_sha256": "a0475687fa620bb89a21a3172f6745da77240b1d711f5abc0d5a5765b1c806c1",
        "log_sha256": "fb424b9170121e6e337fa129f04d65e7b472f9d948c183c4cc4e5ee1a7264fca",
    },
    "latest": {
        "sha": "7882d17aaaaeff9a652b35092808e32ec53b5ce4",
        "url": "https://github.com/jwross24/cairn/actions/runs/36524637482",
        "json_sha256": "55886954457d365873c24a521f91fffdb2645be727ff4fd941355c84c638bafb",
        "log_sha256": "4ad3251cb00b9465f0f66da3d16b9b9cba1139cae8292b7deaf684e33421c7c3",
    },
}
SUMMARY_RE = re.compile(
    r"(?P<passed>[1-9][0-9]*) passed"
    r"(?P<other>(?:, [0-9]+ (?:skipped|deselected|xfailed|failed))*)"
    r" in (?P<pytest_seconds>[0-9]+(?:\.[0-9]+)?)s(?: \([0-9:]+\))?"
)
OTHER_COUNT_RE = re.compile(r", (?P<count>[0-9]+) (?P<name>skipped|deselected|xfailed|failed)")
DURATION_RE = re.compile(r"(?P<seconds>[0-9]+(?:\.[0-9]+)?)s (?P<phase>setup|call|teardown)\s+(?P<node>tests/\S+)")
LANE_RE = re.compile(r"^check \((?P<lane>[^)]+)\)$")


class ProfileError(ValueError):
    pass


def digest(path):
    source = path.read_bytes()
    if path.suffix == ".gz":
        source = gzip.decompress(source)
    return hashlib.sha256(source).hexdigest()


def timestamp_seconds(start, end):
    try:
        first = datetime.fromisoformat(start)
        last = datetime.fromisoformat(end)
    except (AttributeError, TypeError, ValueError):
        raise ProfileError("job has missing or malformed wall-time timestamps") from None
    seconds = (last - first).total_seconds()
    if seconds <= 0:
        raise ProfileError("job has a nonpositive wall time")
    return round(seconds, 2)


def log_fields(line):
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None
    lane_match = LANE_RE.fullmatch(parts[0])
    if lane_match is None:
        return None
    tail = parts[2]
    if "Z " not in tail:
        return None
    return lane_match["lane"], tail.split("Z ", 1)[1]


def summarize_lanes(jobs, log_lines):
    if not isinstance(jobs, list):
        raise ProfileError("run has no job list")
    by_lane = {}
    for job in jobs:
        match = LANE_RE.fullmatch(job.get("name", ""))
        if match is None:
            raise ProfileError(f"malformed job name: {job.get('name')!r}")
        lane = match["lane"]
        if lane in by_lane:
            raise ProfileError(f"duplicate job for lane: {lane}")
        by_lane[lane] = job
    if set(by_lane) != set(LANES):
        missing = sorted(set(LANES) - set(by_lane))
        extra = sorted(set(by_lane) - set(LANES))
        raise ProfileError(f"lane set mismatch; missing={missing}, extra={extra}")

    rows = []
    for lane in LANES:
        job = by_lane[lane]
        if job.get("conclusion") != "success":
            raise ProfileError(f"lane did not pass: {lane}={job.get('conclusion')!r}")
        summaries = []
        for line in log_lines:
            fields = log_fields(line)
            if fields is None or fields[0] != lane:
                continue
            message = fields[1].strip("= \ufeff")
            if not re.match(r"^[0-9]+ passed", message):
                continue
            match = SUMMARY_RE.fullmatch(message)
            if match is None:
                raise ProfileError(f"malformed pytest summary for lane: {lane}")
            counts = {"passed": int(match["passed"])}
            for count in OTHER_COUNT_RE.finditer(match["other"]):
                name = count["name"]
                if name in counts:
                    raise ProfileError(f"duplicate pytest count for lane {lane}: {name}")
                counts[name] = int(count["count"])
            summaries.append((message, line, counts, float(match["pytest_seconds"])))
        if len(summaries) != 1:
            raise ProfileError(f"expected one pytest summary for lane {lane}; found {len(summaries)}")
        summary, source_line, counts, pytest_seconds = summaries[0]
        if pytest_seconds <= 0:
            raise ProfileError(f"lane has a nonpositive pytest time: {lane}")
        rows.append(
            {
                "lane": lane,
                "job_seconds": timestamp_seconds(job["startedAt"], job["completedAt"]),
                "counts": counts,
                "pytest_seconds": pytest_seconds,
                "summary": summary,
                "summary_source_line": source_line,
            }
        )
    return rows


def phase_rows(lanes, log_lines):
    allowed = set(lanes)
    rows = []
    for line in log_lines:
        fields = log_fields(line)
        if fields is None or fields[0] not in allowed:
            continue
        match = DURATION_RE.match(fields[1])
        if match is None:
            continue
        rows.append(
            {
                "lane": fields[0],
                "phase": match["phase"],
                "seconds": float(match["seconds"]),
                "node": match["node"],
                "source_line": line,
            }
        )
    if len(rows) < 10:
        raise ProfileError(f"expected at least ten pytest duration rows; found {len(rows)}")
    return sorted(rows, key=lambda row: (-row["seconds"], row["lane"], row["node"]))


def read_run(label, json_path, log_path):
    expected = RUNS[label]
    if digest(json_path) != expected["json_sha256"]:
        raise ProfileError(f"{label} JSON digest does not match the pinned input")
    if digest(log_path) != expected["log_sha256"]:
        raise ProfileError(f"{label} log digest does not match the pinned input")
    json_bytes = json_path.read_bytes()
    if json_path.suffix == ".gz":
        json_bytes = gzip.decompress(json_bytes)
    payload = json.loads(json_bytes.decode())
    if payload.get("headSha") != expected["sha"]:
        raise ProfileError(f"{label} run SHA does not match the pinned input")
    if payload.get("conclusion") != "success":
        raise ProfileError(f"{label} workflow did not pass")
    if "url" in payload and payload["url"] != expected["url"]:
        raise ProfileError(f"{label} run URL does not match the pinned input")
    log_bytes = log_path.read_bytes()
    if log_path.suffix == ".gz":
        log_bytes = gzip.decompress(log_bytes)
    log_lines = log_bytes.decode("utf-8-sig").splitlines()
    lanes = summarize_lanes(payload.get("jobs"), log_lines)
    setup_steps = [
        {
            "lane": job["name"].removeprefix("check (").removesuffix(")"),
            "seconds": timestamp_seconds(step.get("startedAt"), step.get("completedAt")),
            "source_step": step["name"],
        }
        for job in payload["jobs"]
        for step in job.get("steps", [])
        if step.get("name") == "Install Linux Python build prerequisites"
    ]
    result = {
        "label": label,
        "url": expected["url"],
        "sha": expected["sha"],
        "json_sha256": expected["json_sha256"],
        "log_sha256": expected["log_sha256"],
        "lanes": lanes,
        "linux_prerequisite_steps": setup_steps,
    }
    if label == "latest":
        result["slowest_phases"] = phase_rows(LANES, log_lines)[:10]
    return result, payload, log_lines


def expect_refusal(operation, expected_fragment):
    try:
        operation()
    except ProfileError as exc:
        if expected_fragment not in str(exc):
            raise ProfileError(f"unexpected refusal: {exc}") from None
        return str(exc)
    raise ProfileError(f"expected refusal containing {expected_fragment!r}")


def self_test(payload, log_lines):
    jobs_without_lane = [job for job in payload["jobs"] if job["name"] != "check (container)"]
    missing_lane = expect_refusal(
        lambda: summarize_lanes(jobs_without_lane, log_lines),
        "lane set mismatch",
    )
    container_summaries = []
    for line in log_lines:
        fields = log_fields(line)
        if fields is None or fields[0] != "container":
            continue
        normalized = fields[1].strip("= \ufeff")
        if re.match(r"^[0-9]+ passed", normalized):
            container_summaries.append(line)
    if len(container_summaries) != 1:
        raise ProfileError("self-test could not isolate the container summary")
    malformed = [line for line in log_lines if line != container_summaries[0]]
    malformed.append(container_summaries[0].replace("21 passed", "21 pass"))
    malformed_summary = expect_refusal(
        lambda: summarize_lanes(payload["jobs"], malformed),
        "expected one pytest summary for lane container; found 0",
    )
    return {
        "missing_lane_refused": missing_lane,
        "malformed_summary_refused": malformed_summary,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-json", type=Path, required=True)
    parser.add_argument("--baseline-log", type=Path, required=True)
    parser.add_argument("--latest-json", type=Path, required=True)
    parser.add_argument("--latest-log", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    baseline, _, _ = read_run("baseline", args.baseline_json, args.baseline_log)
    latest, payload, log_lines = read_run("latest", args.latest_json, args.latest_log)
    output = {"runs": [baseline, latest]}
    if args.self_test:
        output["refusal_checks"] = self_test(payload, log_lines)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, json.JSONDecodeError, ProfileError) as exc:
        print(f"profile_ci: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
