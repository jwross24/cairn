from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

RUN_ID = 36540366017
PILOT_SHA = "09a8a03852ca3473abaae0ce87c907b6aafdee82"
BASELINE_SHA = "bf8662704e1414e0d4f3a82200d660dacc231290"
JSON_SHA256 = "af4eb21c7b582952e3a0ba154ac85baba1bc22c6df21d148c3744d8211ac402e"
LOG_SHA256 = "813b62e1208e679ba9570f4ce164f4c0f08d093d2a0f39e153e2d02e001d6841"
JSON_GZIP_SHA256 = "fb450f25a0ee1086259f675449ff3725745b82fb17d3c06b00ffe8f166c29f8c"
LOG_GZIP_SHA256 = "0d9c287633d8ff1a55f76860ef19cfce8adf9eb740dc44a8da0bbcf2f43a4d38"
HELPER_SHA256 = "905f21d4914cd4ce59c76dfc86b60c4d14bd2b8a40875900e284c519c8a2d36f"
PYTHON_NODE = "tests/unit/test_ci_lanes.py::test_every_direct_lean_import_has_one_explicit_lane_classification"

ROOT = Path(__file__).resolve().parents[5]
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "pilot_profile", ROOT / "research/grounding/test-architecture-2026-09-29/pilot_profile.py"
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:
    raise RuntimeError("pilot profile parser is unavailable")
profile = importlib.util.module_from_spec(PROFILE_SPEC)
sys.modules[PROFILE_SPEC.name] = profile
PROFILE_SPEC.loader.exec_module(profile)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise profile.ProfileError(reason)


def step_rows(summary: dict) -> dict[str, dict]:
    return {row["name"]: row for row in summary["gate_setup_cache_step_durations"]}


def main() -> None:
    run_dir = Path(__file__).resolve().parent
    json_path = run_dir / "run.json.gz"
    log_path = run_dir / "run.log.gz"
    json_raw, json_data = profile.read_input(json_path)
    log_raw, log_data = profile.read_input(log_path)
    require(hashlib.sha256(json_data).hexdigest() == JSON_SHA256, "run JSON content digest mismatch")
    require(hashlib.sha256(log_data).hexdigest() == LOG_SHA256, "run log content digest mismatch")
    require(hashlib.sha256(json_raw).hexdigest() == JSON_GZIP_SHA256, "run JSON gzip digest mismatch")
    require(hashlib.sha256(log_raw).hexdigest() == LOG_GZIP_SHA256, "run log gzip digest mismatch")
    payload = json.loads(json_data.decode("utf-8-sig"))
    require(payload.get("databaseId") == RUN_ID, "run ID mismatch")
    require(payload.get("status") == "completed", "run is not terminal")
    require(payload.get("conclusion") == "failure", "run is not the retained failed run")
    require(payload.get("headSha") == PILOT_SHA, "pilot source SHA mismatch")
    require(
        hashlib.sha256((ROOT / "tests/_linux_dependencies.py").read_bytes()).hexdigest() == HELPER_SHA256,
        "Linux dependency helper digest mismatch",
    )

    jobs = {}
    for job in payload.get("jobs", []):
        match = profile.LANE_RE.fullmatch(job.get("name", ""))
        if match is not None:
            lane = match["lane"]
            require(lane not in jobs, f"duplicate lane job: {lane}")
            jobs[lane] = job
    require(set(jobs) == set(profile.LANES), "run lane set mismatch")

    log_lines = log_data.decode("utf-8-sig").splitlines()
    lane_logs = {lane: [] for lane in profile.LANES}
    for line in log_lines:
        fields = profile.log_fields(line)
        if fields is not None and fields[0] in lane_logs:
            lane_logs[fields[0]].append((fields[1], fields[2], line))

    summaries = {
        lane: profile.summarize_lane(lane, jobs[lane], lane_logs[lane]) for lane in ("python", *profile.LINUX_LANES)
    }
    transport = profile.transport_profile(payload["headSha"], jobs, lane_logs)
    python = summaries["python"]
    failure_evidence = []
    for _, message, source_line in lane_logs["python"]:
        if any(
            marker in message
            for marker in (
                f"{PYTHON_NODE} FAILED",
                ">       assert imports == (lean - indirect_lean) | python_only",
                "E         Extra items in the left set:",
                "E         'tests/unit/test_linux_dependency_cache.py'",
                "tests/unit/test_ci_lanes.py:432: AssertionError",
                "1 failed, 4220 passed, 2 skipped, 181 deselected, 1 xfailed",
            )
        ):
            failure_evidence.append(source_line)
    require(len(failure_evidence) == 6, "Python failure evidence is incomplete")
    require(
        python["counts"]
        == {
            "passed": 4220,
            "failed": 1,
            "errors": 0,
            "skipped": 2,
            "deselected": 181,
            "xfailed": 1,
            "xpassed": 0,
            "warnings": 0,
        },
        "Python pytest counts differ from the retained failure",
    )

    linux = []
    keys = set()
    for lane in profile.LINUX_LANES:
        summary = summaries[lane]
        row = transport["per_lane"][lane]
        restore = row["restore"]
        require(summary["job_conclusion"] == "success", f"Linux lane did not pass: {lane}")
        require(restore["status"] == "miss", f"Linux prerequisite cache did not miss: {lane}")
        require(len(restore["key_evidence"]) == 1, f"missing cache miss evidence: {lane}")
        require(row["import"]["status"] == "skipped", f"Linux archive import was not skipped: {lane}")
        require(row["prepare"]["status"] == "prepared_with_events", f"Linux preparation was not observed: {lane}")
        keys.add(restore["key_evidence"][0]["key"])
        steps = step_rows(summary)
        required_steps = (
            "Identify Linux prerequisite cache",
            "Restore Linux prerequisite cache",
            "Import cached Linux prerequisites",
            "Prepare Linux prerequisites",
            "Linux container gates",
            "Export Linux prerequisites",
            "Save Linux prerequisite cache",
        )
        require(all(name in steps for name in required_steps), f"missing lane stage timing: {lane}")
        linux.append(
            {
                "lane": lane,
                "job_conclusion": summary["job_conclusion"],
                "job_seconds": summary["job_seconds"],
                "counts": summary["counts"],
                "reported_count_fields": summary["reported_count_fields"],
                "collected_count": summary["collected_count"],
                "pytest_seconds": summary["pytest_seconds"],
                "pytest_summary_source_line": summary["summary_source_line"],
                "cache_restore": {
                    "status": restore["status"],
                    "key": restore["key_evidence"][0]["key"],
                    "source_line": restore["key_evidence"][0]["source_line"],
                },
                "stages": {
                    name: {
                        "conclusion": steps[name]["conclusion"],
                        "seconds": steps[name]["duration_seconds"],
                    }
                    for name in required_steps
                },
            }
        )
    require(len(keys) == 1, "Linux prerequisite cache misses used different keys")
    require(transport["dependency_archive_cache"]["status"] == "miss", "cache miss classification mismatch")
    require(transport["publication"]["status"] == "published", "archive publication evidence is incomplete")
    for lane in profile.LINUX_LANES:
        if lane == "container":
            continue
        require(transport["per_lane"][lane]["export"]["status"] == "skipped", f"unexpected export lane: {lane}")
        require(transport["per_lane"][lane]["save"]["status"] == "skipped", f"unexpected save lane: {lane}")
    export_line = transport["publication"]["export"]["event_lines"]
    save_line = transport["publication"]["save"]["save_evidence"]
    require(len(export_line) == 1 and len(save_line) == 1, "archive publication source lines are incomplete")
    export_fields = profile.log_fields(export_line[0])
    export_event = json.loads(export_fields[2])
    save_fields = profile.log_fields(save_line[0])
    save_match = profile.CACHE_SAVE_RE.search(save_fields[2])
    require(
        save_match is not None and save_match["key"].strip() == next(iter(keys)),
        "saved cache key does not match the restore key",
    )
    require(export_event.get("event") == "archive_published", "archive event mismatch")
    require(export_event.get("image_id"), "published archive image ID is absent")

    report = {
        "record_kind": "failed_run_observation",
        "status": "failed",
        "run": {
            "id": RUN_ID,
            "status": payload["status"],
            "conclusion": payload["conclusion"],
            "event": payload.get("event"),
            "workflow_name": payload.get("workflowName"),
            "source_sha": payload["headSha"],
            "started_at": payload.get("startedAt"),
            "updated_at": payload.get("updatedAt"),
            "url": payload.get("url"),
        },
        "source_scope": {
            "baseline_source_sha": BASELINE_SHA,
            "pilot_source_sha": PILOT_SHA,
            "linux_dependency_helper_sha256": HELPER_SHA256,
            "profile_parser_sha256": hashlib.sha256(
                (ROOT / "research/grounding/test-architecture-2026-09-29/pilot_profile.py").read_bytes()
            ).hexdigest(),
            "baseline_run_id": 36536577420,
            "baseline_profile": "research/grounding/test-architecture-2026-09-29/pilot-runs/run-36536577420/profile.json",
        },
        "raw_inputs": {
            "json": {
                "path": "research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/run.json.gz",
                "compressed_sha256": hashlib.sha256(json_raw).hexdigest(),
                "content_sha256": hashlib.sha256(json_data).hexdigest(),
                "compressed_bytes": len(json_raw),
                "content_bytes": len(json_data),
            },
            "log": {
                "path": "research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/run.log.gz",
                "compressed_sha256": hashlib.sha256(log_raw).hexdigest(),
                "content_sha256": hashlib.sha256(log_data).hexdigest(),
                "compressed_bytes": len(log_raw),
                "content_bytes": len(log_data),
            },
        },
        "python_failure": {
            "job_conclusion": python["job_conclusion"],
            "job_seconds": python["job_seconds"],
            "counts": python["counts"],
            "reported_count_fields": python["reported_count_fields"],
            "collected_count": python["collected_count"],
            "pytest_seconds": python["pytest_seconds"],
            "failing_node": PYTHON_NODE,
            "reason": "The import-set equality assertion saw tests/unit/test_linux_dependency_cache.py as an extra direct Lean import; the expected classified set omitted that path.",
            "assertion_location": "tests/unit/test_ci_lanes.py:432",
            "source_lines": failure_evidence,
        },
        "linux_lanes": linux,
        "cache_observation": {
            "linux_prerequisite_cache": "miss",
            "same_key_across_five_lanes": next(iter(keys)),
            "action_cache_miss_evidence_count": len(linux),
            "archive_imported": False,
            "archive_import_steps": {
                lane: {
                    "status": transport["per_lane"][lane]["import"]["status"],
                    "step_conclusion": transport["per_lane"][lane]["import"]["step_conclusion"],
                }
                for lane in profile.LINUX_LANES
            },
        },
        "publication": {
            "status": "published by the container lane",
            "image_id": export_event["image_id"],
            "archive_published_source_line": export_line[0],
            "cache_save_status": "saved",
            "cache_save_source_line": save_line[0],
            "saved_key_matches_five_restore_keys": True,
        },
        "profile_cli_negative": {
            "command": "uv run python research/grounding/test-architecture-2026-09-29/pilot_profile.py --run-json research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/run.json.gz --run-log research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/run.log.gz",
            "exit_code": 2,
            "refusal": "run failed: conclusion='failure'",
        },
        "claims_not_supported": [
            "CI speedup",
            "overall CI success",
            "full audit coverage",
            "skip-free non-Linux execution",
            "warm-cache performance",
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
