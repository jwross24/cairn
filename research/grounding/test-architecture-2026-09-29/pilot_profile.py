from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import tempfile
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
    "container-plan-exact",
    "container-plan-refusals",
)
LINUX_LANES = (
    "container",
    "container-replay-exact",
    "container-replay-refusals",
    "container-plan-exact",
    "container-plan-refusals",
)
BASELINE_SHA = "bf8662704e1414e0d4f3a82200d660dacc231290"
BASELINE_WORKFLOW_SHA256 = "3e316b4ce070855aa2605d2f7951ed9706046d670cf36a142fbd2cb9eadbdda3f"
BASELINE_TRANSPORT_STEPS = (
    "restore linux prerequisite cache",
    "import cached linux prerequisites",
    "prepare linux prerequisites",
    "export linux prerequisites",
    "save linux prerequisite cache",
)
LANE_RE = re.compile(r"^check \((?P<lane>[^)]+)\)$")
SUMMARY_RE = re.compile(
    r"^=+\s*(?P<body>.+?)\s+in\s+(?P<seconds>[0-9]+(?:\.[0-9]+)?)s"
    r"(?:\s+\([^)]*\))?\s*=+$"
)
SUMMARY_ITEM_RE = re.compile(
    r"^(?P<count>[0-9]+) (?P<name>passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?)$"
)
SUMMARY_CANDIDATE_RE = re.compile(r"^=+.*\bin\s+[0-9]+(?:\.[0-9]+)?s\b")
COLLECTED_RE = re.compile(r"\bcollected (?P<count>[0-9]+) items?\b", re.IGNORECASE)
DURATION_RE = re.compile(
    r"^\s*(?P<seconds>[0-9]+(?:\.[0-9]+)?)s\s+"
    r"(?P<phase>setup|call|teardown)\s+(?P<node>tests/\S+)\s*$"
)
LOG_TIMESTAMP_RE = re.compile(r"^\ufeff?[0-9]{4}-[0-9]{2}-[0-9]{2}T[^ ]+Z\s*")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CACHE_SIGNAL_RE = re.compile(
    r"(?:Cache hit for:|Cache restored from key:|Cache not found for input keys:)\s*(?P<key>.*)$",
    re.IGNORECASE,
)
CACHE_SAVE_RE = re.compile(
    r"(?:Cache saved with key:|Cache saved successfully|Saved cache with key:)\s*(?P<key>.*)$",
    re.IGNORECASE,
)
EVENT_RE = re.compile(r"\b(archive_imported|archive_published|archive_hit|validated|provisioned|published|hit)\b")
COUNT_KEYS = ("passed", "failed", "errors", "skipped", "deselected", "xfailed", "xpassed", "warnings")


class ProfileError(ValueError):
    pass


def read_input(path: Path) -> tuple[bytes, bytes]:
    try:
        raw = path.read_bytes()
        data = gzip.decompress(raw) if path.suffix == ".gz" else raw
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        raise ProfileError(f"cannot read input {path}: {type(exc).__name__}") from None
    return raw, data


def timestamp_seconds(start: object, end: object, label: str, allow_zero: bool = False) -> float:
    try:
        first = datetime.fromisoformat(str(start))
        last = datetime.fromisoformat(str(end))
        seconds = (last - first).total_seconds()
    except TypeError, ValueError, OverflowError:
        raise ProfileError(f"{label} has missing or malformed wall-time timestamps") from None
    if seconds < 0 or (seconds == 0 and not allow_zero):
        raise ProfileError(f"{label} has a nonpositive wall time")
    return round(seconds, 3)


def log_fields(line: str) -> tuple[str, str, str] | None:
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None
    lane_match = LANE_RE.fullmatch(parts[0])
    if lane_match is None:
        return None
    message = LOG_TIMESTAMP_RE.sub("", parts[2], count=1)
    return lane_match["lane"], parts[1], ANSI_RE.sub("", message)


def lane_jobs(jobs: object) -> dict[str, dict]:
    if not isinstance(jobs, list):
        raise ProfileError("run has no job list")
    by_lane = {}
    for job in jobs:
        if not isinstance(job, dict):
            raise ProfileError("run job entry is malformed")
        match = LANE_RE.fullmatch(job.get("name", ""))
        if match is None:
            continue
        lane = match["lane"]
        if lane in by_lane:
            raise ProfileError(f"duplicate job for lane: {lane}")
        by_lane[lane] = job
    if set(by_lane) != set(LANES):
        missing = sorted(set(LANES) - set(by_lane))
        extra = sorted(set(by_lane) - set(LANES))
        raise ProfileError(f"lane set mismatch; missing={missing}, extra={extra}")
    for lane in LANES:
        if by_lane[lane].get("conclusion") != "success":
            raise ProfileError(f"lane did not pass: {lane}={by_lane[lane].get('conclusion')!r}")
    return by_lane


def parse_summary(message: str, lane: str, source_line: str) -> dict:
    match = SUMMARY_RE.fullmatch(message.strip())
    if match is None:
        raise ProfileError(f"malformed pytest summary for lane: {lane}")
    counts = dict.fromkeys(COUNT_KEYS, 0)
    reported = []
    for part in match["body"].split(", "):
        item = SUMMARY_ITEM_RE.fullmatch(part.strip())
        if item is None:
            raise ProfileError(f"malformed pytest summary for lane: {lane}")
        name = item["name"]
        key = "errors" if name in ("error", "errors") else "warnings" if name in ("warning", "warnings") else name
        if key in reported:
            raise ProfileError(f"duplicate pytest count for lane {lane}: {key}")
        counts[key] = int(item["count"])
        reported.append(key)
    if not reported:
        raise ProfileError(f"malformed pytest summary for lane: {lane}")
    seconds = float(match["seconds"])
    if seconds <= 0:
        raise ProfileError(f"lane has a nonpositive pytest time: {lane}")
    return {
        "counts": counts,
        "reported_count_fields": reported,
        "pytest_seconds": seconds,
        "summary": message.strip(),
        "summary_source_line": source_line,
    }


def summarize_lane(lane: str, job: dict, entries: list[tuple[str, str, str]]) -> dict:
    candidates = [
        (message, source_line) for _, message, source_line in entries if SUMMARY_CANDIDATE_RE.match(message.strip())
    ]
    if len(candidates) != 1:
        raise ProfileError(f"expected one pytest summary for lane {lane}; found {len(candidates)}")
    summary = parse_summary(candidates[0][0], lane, candidates[0][1])
    collected = [
        (int(match["count"]), source_line)
        for _, message, source_line in entries
        if (match := COLLECTED_RE.search(message)) is not None
    ]
    if len(collected) > 1:
        raise ProfileError(f"expected at most one pytest collection count for lane {lane}; found {len(collected)}")
    if collected:
        collected_count, collection_source_line = collected[0]
        collection_status = "reported"
    else:
        collected_count = None
        collection_source_line = None
        collection_status = "absent"
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        raise ProfileError(f"lane has malformed step list: {lane}")
    first_gate = next((index for index, step in enumerate(steps) if gate_boundary(step)), len(steps))
    step_durations = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ProfileError(f"lane has malformed step entry: {lane}")
        categories = step_categories(step, entries, index < first_gate)
        if not categories:
            continue
        if step.get("startedAt") is None or step.get("completedAt") is None:
            duration = None
            timing_status = "timestamps_absent"
        else:
            duration = timestamp_seconds(
                step.get("startedAt"), step.get("completedAt"), f"step {step.get('name')!r}", allow_zero=True
            )
            timing_status = "measured"
        step_durations.append(
            {
                "name": step.get("name"),
                "status": step.get("status"),
                "conclusion": step.get("conclusion"),
                "categories": categories,
                "duration_seconds": duration,
                "timing_status": timing_status,
            }
        )
    return {
        "lane": lane,
        "job_conclusion": job.get("conclusion"),
        "job_seconds": timestamp_seconds(job.get("startedAt"), job.get("completedAt"), f"job {lane}"),
        "counts": summary["counts"],
        "reported_count_fields": summary["reported_count_fields"],
        "collected_count": collected_count,
        "collection_status": collection_status,
        "collection_source_line": collection_source_line,
        "pytest_seconds": summary["pytest_seconds"],
        "summary": summary["summary"],
        "summary_source_line": summary["summary_source_line"],
        "gate_setup_cache_step_durations": step_durations,
    }


def step_categories(step: dict, entries: list[tuple[str, str, str]], before_gate: bool) -> list[str]:
    name = str(step.get("name", ""))
    lowered = name.lower()
    matching = [message for step_name, message, _ in entries if step_name == name]
    categories = []
    transport_step = "linux prerequisite" in lowered and any(
        word in lowered for word in ("import", "prepare", "export")
    )
    if (
        any(word in lowered for word in ("cache", "restore", "save"))
        or transport_step
        or any(CACHE_SIGNAL_RE.search(message) for message in matching)
    ):
        categories.append("cache")
    if gate_step(step):
        categories.append("gate")
    if (
        before_gate
        and "gate" not in categories
        and not lowered.startswith("post ")
        and lowered
        not in (
            "complete job",
            "test diagnostics",
        )
    ):
        categories.append("setup")
    return categories


def gate_step(step: dict) -> bool:
    return str(step.get("name", "")).lower() in ("gates", "linux container gates", "linux adapter types")


def gate_boundary(step: dict) -> bool:
    return str(step.get("name", "")).lower() in ("gates", "linux container gates")


def require_category_contract(name: str, observed: list[str], expected: list[str]) -> None:
    if observed != expected:
        raise ProfileError(f"step category mismatch for {name!r}: observed={observed}, expected={expected}")


def phase_rows(lanes: dict[str, list[tuple[str, str, str]]]) -> list[dict]:
    rows = []
    for lane, entries in lanes.items():
        for _, message, source_line in entries:
            match = DURATION_RE.fullmatch(message)
            if match is not None:
                rows.append(
                    {
                        "lane": lane,
                        "phase": match["phase"],
                        "seconds": float(match["seconds"]),
                        "node": match["node"],
                        "source_line": source_line,
                    }
                )
    return sorted(rows, key=lambda row: (-row["seconds"], row["lane"], row["node"]))[:10]


def find_step(job: dict, fragment: str) -> dict | None:
    matches = [step for step in job.get("steps", []) if fragment in str(step.get("name", "")).lower()]
    if len(matches) > 1:
        raise ProfileError(f"multiple steps match {fragment!r} in {job.get('name')!r}")
    return matches[0] if matches else None


def matching_entries(entries: list[tuple[str, str, str]], step: dict | None) -> list[tuple[str, str, str]]:
    if step is None:
        return []
    return [entry for entry in entries if entry[0] == step.get("name")]


def step_status(step: dict | None, entries: list[tuple[str, str, str]]) -> dict:
    if step is None:
        return {"status": "absent"}
    raw = matching_entries(entries, step)
    return {
        "status": step.get("status", "unknown"),
        "conclusion": step.get("conclusion", "unknown"),
        "evidence_lines": [source_line for _, _, source_line in raw if EVENT_RE.search(source_line)],
    }


def cache_signal(step: dict | None, entries: list[tuple[str, str, str]]) -> dict:
    if step is None:
        return {"status": "absent", "key_evidence": []}
    signals = []
    for _, message, source_line in matching_entries(entries, step):
        match = CACHE_SIGNAL_RE.search(message)
        if match is None:
            continue
        marker = message.split(":", 1)[0].strip().lower()
        outcome = "hit" if marker in ("cache hit for", "cache restored from key") else "miss"
        signals.append({"outcome": outcome, "key": match["key"].strip(), "source_line": source_line})
    outcomes = {signal["outcome"] for signal in signals}
    if len(outcomes) == 1:
        status = outcomes.pop()
    elif outcomes:
        status = "conflicting"
    else:
        status = "unknown"
    return {"status": status, "key_evidence": signals}


def event_status(step: dict | None, entries: list[tuple[str, str, str]], event: str) -> dict:
    status = step_status(step, entries)
    if status["status"] == "absent":
        return {"status": "absent", "event_lines": []}
    event_lines = [
        source_line
        for _, _, source_line in matching_entries(entries, step)
        if re.search(rf"\b{re.escape(event)}\b", source_line)
    ]
    if status["conclusion"] == "failure":
        outcome = "failed"
    elif status["conclusion"] == "skipped":
        outcome = "skipped"
    elif status["conclusion"] == "success" and event_lines:
        outcome = event
    elif status["conclusion"] == "success":
        outcome = "success_without_event"
    else:
        outcome = "unknown"
    return {"status": outcome, "step_conclusion": status["conclusion"], "event_lines": event_lines}


def save_status(step: dict | None, entries: list[tuple[str, str, str]]) -> dict:
    status = step_status(step, entries)
    if status["status"] == "absent":
        return {"status": "absent", "save_evidence": []}
    evidence = []
    for _, message, source_line in matching_entries(entries, step):
        if CACHE_SAVE_RE.search(message):
            evidence.append(source_line)
    if status["conclusion"] == "failure":
        outcome = "failed"
    elif status["conclusion"] == "skipped":
        outcome = "skipped"
    elif status["conclusion"] == "success" and evidence:
        outcome = "saved"
    elif status["conclusion"] == "success":
        outcome = "success_without_save_evidence"
    else:
        outcome = "unknown"
    return {"status": outcome, "step_conclusion": status["conclusion"], "save_evidence": evidence}


def transport_profile(
    source_sha: str, by_lane: dict[str, dict], lane_logs: dict[str, list[tuple[str, str, str]]]
) -> dict:
    per_lane = {}
    for lane in LANES:
        job = by_lane[lane]
        entries = lane_logs[lane]
        key_step = find_step(job, "identify linux prerequisite cache")
        restore_step = find_step(job, "restore linux prerequisite cache")
        import_step = find_step(job, "import cached linux prerequisites")
        prepare_step = find_step(job, "prepare linux prerequisites")
        export_step = find_step(job, "export linux prerequisites")
        save_step = find_step(job, "save linux prerequisite cache")
        key_lines = [
            source_line
            for step_name, message, source_line in entries
            if (key_step and step_name == key_step.get("name") and "key" in message.lower())
            or (restore_step and step_name == restore_step.get("name") and CACHE_SIGNAL_RE.search(message))
        ]
        prepare_events = [
            source_line
            for _, _, source_line in matching_entries(entries, prepare_step)
            if re.search(r"\b(validated|provisioned|published|hit)\b", source_line)
        ]
        prepare_observation = step_status(prepare_step, entries)
        if prepare_observation["status"] == "absent":
            prepare_status = "absent"
        elif prepare_observation["conclusion"] == "failure":
            prepare_status = "failed"
        elif prepare_observation["conclusion"] == "skipped":
            prepare_status = "skipped"
        elif prepare_observation["conclusion"] == "success" and prepare_events:
            prepare_status = "prepared_with_events"
        elif prepare_observation["conclusion"] == "success":
            prepare_status = "success_without_prepare_event"
        else:
            prepare_status = "unknown"
        per_lane[lane] = {
            "cache_key_evidence": key_lines,
            "restore": cache_signal(restore_step, entries),
            "import": event_status(import_step, entries, "archive_imported"),
            "prepare": {
                "status": prepare_status,
                "step_conclusion": prepare_observation.get("conclusion"),
                "event_lines": prepare_events,
            },
            "export": event_status(export_step, entries, "archive_published"),
            "save": save_status(save_step, entries),
        }
    configured = any(
        per_lane[lane][key]["status"] != "absent"
        for lane in LANES
        for key in ("restore", "import", "prepare", "export", "save")
    )
    baseline_source_evidence = {
        "workflow": f".github/workflows/ci.yml@{BASELINE_SHA}",
        "workflow_sha256": BASELINE_WORKFLOW_SHA256,
        "checked_for_steps": list(BASELINE_TRANSPORT_STEPS),
        "observation": "the pinned baseline workflow contains no Linux prerequisite archive transport steps",
    }
    if source_sha == BASELINE_SHA and not configured:
        cache_state = "not-configured"
        cache_evidence = baseline_source_evidence
    elif not configured:
        cache_state = "unknown"
        cache_evidence = {"reason": "no dependency-archive transport steps appear in the captured run"}
    else:
        linux = [per_lane[lane] for lane in LINUX_LANES]
        restores = [row["restore"]["status"] for row in linux]
        if all(value == "hit" for value in restores) and all(
            row["import"]["status"] == "archive_imported" for row in linux
        ):
            cache_state = "hit"
        elif all(value == "miss" for value in restores) and all(
            row["prepare"]["status"] == "prepared_with_events" for row in linux
        ):
            cache_state = "miss"
        elif "hit" in restores and "miss" in restores:
            cache_state = "mixed"
        else:
            cache_state = "unknown"
        cache_evidence = {
            "reason": "classification uses action cache log signals and observed import/prepare step outcomes"
        }
    container = per_lane["container"]
    export_state = container["export"]["status"]
    save_state = container["save"]["status"]
    if export_state == "archive_published" and save_state == "saved":
        publication_state = "published"
    elif not configured:
        publication_state = "not-configured" if source_sha == BASELINE_SHA else "unknown"
    elif export_state == "skipped" or save_state == "skipped":
        publication_state = "not-run"
    else:
        publication_state = "unknown"
    return {
        "dependency_archive_cache": {"status": cache_state, "evidence": cache_evidence},
        "publication": {"status": publication_state, "export": container["export"], "save": container["save"]},
        "per_lane": per_lane,
    }


def build_report(
    payload: dict,
    log_lines: list[str],
    json_raw: bytes,
    json_data: bytes,
    log_raw: bytes,
    log_data: bytes,
    json_path: Path,
    log_path: Path,
) -> dict:
    if payload.get("status") != "completed":
        raise ProfileError(f"run is not terminal: status={payload.get('status')!r}")
    if payload.get("conclusion") != "success":
        raise ProfileError(f"run failed: conclusion={payload.get('conclusion')!r}")
    source_sha = payload.get("headSha")
    if not isinstance(source_sha, str) or not source_sha:
        raise ProfileError("run has no source SHA")
    by_lane = lane_jobs(payload.get("jobs"))
    lane_logs = {lane: [] for lane in LANES}
    for line in log_lines:
        fields = log_fields(line)
        if fields is not None and fields[0] in lane_logs:
            lane_logs[fields[0]].append((fields[1], fields[2], line))
    lanes = [summarize_lane(lane, by_lane[lane], lane_logs[lane]) for lane in LANES]
    run_id = payload.get("databaseId")
    return {
        "source_scope": {
            "source_sha": source_sha,
            "extractor_path": str(Path(__file__).resolve()),
            "extractor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "run_id": run_id,
            "run_url": payload.get("url"),
            "lane_set": list(LANES),
            "lane_count": len(LANES),
            "test_counts_scope": "pytest summaries from the selected CI lane invocations; deselected, skipped, xfailed, and xpassed counts remain separate",
            "claims_not_supported": [
                "CI speedup",
                "full audit coverage",
                "skip-free execution",
                "isolated function cost from pytest phase timings",
                "results for any future pilot run",
            ],
        },
        "run": {
            "status": payload.get("status"),
            "conclusion": payload.get("conclusion"),
            "event": payload.get("event"),
            "workflow_name": payload.get("workflowName"),
            "started_at": payload.get("startedAt"),
            "updated_at": payload.get("updatedAt"),
            "json_input": {
                "path": str(json_path),
                "compressed_sha256": hashlib.sha256(json_raw).hexdigest(),
                "content_sha256": hashlib.sha256(json_data).hexdigest(),
            },
            "log_input": {
                "path": str(log_path),
                "compressed_sha256": hashlib.sha256(log_raw).hexdigest(),
                "content_sha256": hashlib.sha256(log_data).hexdigest(),
            },
        },
        "linux_prerequisite_transport": transport_profile(source_sha, by_lane, lane_logs),
        "lanes": lanes,
        "top_test_phase_timings": phase_rows(lane_logs),
    }


def expect_refusal(operation, expected_fragment: str) -> str:
    try:
        operation()
    except ProfileError as exc:
        if expected_fragment not in str(exc):
            raise ProfileError(f"self-test got an unexpected refusal: {exc}") from None
        return str(exc)
    raise ProfileError(f"self-test expected refusal containing {expected_fragment!r}")


def self_test(payload: dict, log_lines: list[str], json_data: bytes, log_data: bytes) -> dict:
    root = Path(tempfile.mkdtemp(prefix="cairn-pilot-profile-self-test-"))
    missing_dir = root / "missing-lane"
    malformed_dir = root / "malformed-summary"
    missing_dir.mkdir()
    malformed_dir.mkdir()
    missing_payload = json.loads(json_data.decode("utf-8-sig"))
    missing_payload["jobs"] = [job for job in missing_payload["jobs"] if job.get("name") != "check (container)"]
    missing_json = missing_dir / "run.json"
    missing_log = missing_dir / "run.log"
    missing_json.write_text(json.dumps(missing_payload), encoding="utf-8")
    missing_log.write_bytes(log_data)
    missing_lane = expect_refusal(lambda: lane_jobs(missing_payload.get("jobs")), "lane set mismatch")
    damaged_lines = list(log_lines)
    container_summary = next(
        (
            line
            for line in damaged_lines
            if (fields := log_fields(line))
            and fields[0] == "container"
            and SUMMARY_CANDIDATE_RE.match(fields[2].strip())
        ),
        None,
    )
    if container_summary is None:
        raise ProfileError("self-test cannot locate the container pytest summary")
    damaged_summary = container_summary.replace("passed", "pass", 1)
    if damaged_summary == container_summary:
        raise ProfileError("self-test cannot corrupt the container pytest summary")
    malformed_bytes = log_data.replace(container_summary.encode("utf-8"), damaged_summary.encode("utf-8"), 1)
    if malformed_bytes == log_data:
        raise ProfileError("self-test cannot write an independent malformed log copy")
    malformed_json = malformed_dir / "run.json"
    malformed_log = malformed_dir / "run.log"
    malformed_json.write_bytes(json_data)
    malformed_log.write_bytes(malformed_bytes)
    malformed_lines = malformed_bytes.decode("utf-8-sig").splitlines()
    container_entries = [
        (fields[1], fields[2], line)
        for line in malformed_lines
        if (fields := log_fields(line)) and fields[0] == "container"
    ]
    malformed_summary_refusal = expect_refusal(
        lambda: summarize_lane("container", lane_jobs(payload.get("jobs"))["container"], container_entries),
        "malformed pytest summary for lane: container",
    )
    gate_categories = step_categories({"name": "Linux container gates"}, [], True)
    require_category_contract("Linux container gates", gate_categories, ["gate"])
    gate_setup_refusal = expect_refusal(
        lambda: require_category_contract("Linux container gates", ["gate", "setup"], ["gate"]),
        "step category mismatch",
    )
    toolchain_categories = step_categories({"name": "The Lean toolchain the gate resolves"}, [], True)
    require_category_contract("The Lean toolchain the gate resolves", toolchain_categories, ["setup"])
    toolchain_gate_refusal = expect_refusal(
        lambda: require_category_contract("The Lean toolchain the gate resolves", ["gate"], ["setup"]),
        "step category mismatch",
    )
    export_categories = step_categories({"name": "Export Linux prerequisites"}, [], False)
    require_category_contract("Export Linux prerequisites", export_categories, ["cache"])
    export_setup_refusal = expect_refusal(
        lambda: require_category_contract("Export Linux prerequisites", ["cache", "setup"], ["cache"]),
        "step category mismatch",
    )
    nonterminal_payload = json.loads(json_data.decode("utf-8-sig"))
    nonterminal_payload["status"] = "in_progress"
    nonterminal_refusal = expect_refusal(
        lambda: build_report(nonterminal_payload, log_lines, b"", b"", b"", b"", Path("run.json"), Path("run.log")),
        "run is not terminal",
    )
    failed_payload = json.loads(json_data.decode("utf-8-sig"))
    failed_payload["conclusion"] = "failure"
    failed_refusal = expect_refusal(
        lambda: build_report(failed_payload, log_lines, b"", b"", b"", b"", Path("run.json"), Path("run.log")),
        "run failed",
    )
    return {
        "status": "passed",
        "retained_scratch_root": str(root),
        "missing_lane": {
            "status": "refused",
            "reason": missing_lane,
            "json_copy": str(missing_json),
            "log_copy": str(missing_log),
        },
        "malformed_summary": {
            "status": "refused",
            "reason": malformed_summary_refusal,
            "json_copy": str(malformed_json),
            "log_copy": str(malformed_log),
        },
        "step_category_contract": {
            "status": "passed",
            "gate_categories": gate_categories,
            "planted_gate_as_setup": {"status": "refused", "reason": gate_setup_refusal},
            "toolchain_setup_categories": toolchain_categories,
            "planted_toolchain_as_gate": {"status": "refused", "reason": toolchain_gate_refusal},
            "post_gate_export_categories": export_categories,
            "planted_export_as_setup": {"status": "refused", "reason": export_setup_refusal},
        },
        "run_state_refusals": {
            "nonterminal": {"status": "refused", "reason": nonterminal_refusal},
            "failed": {"status": "refused", "reason": failed_refusal},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", required=True, type=Path)
    parser.add_argument("--run-log", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        json_raw, json_data = read_input(args.run_json)
        log_raw, log_data = read_input(args.run_log)
        payload = json.loads(json_data.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ProfileError("run JSON root is not an object")
        log_lines = log_data.decode("utf-8-sig").splitlines()
        report = build_report(payload, log_lines, json_raw, json_data, log_raw, log_data, args.run_json, args.run_log)
        if args.self_test:
            report["planted_refusals"] = self_test(payload, log_lines, json_data, log_data)
    except (ProfileError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
