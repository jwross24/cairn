"""Capture dispatch and control request bodies from the pinned Claude CLI."""

import asyncio
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import claude_agent_sdk
from claude_agent_sdk import ClaudeSDKClient, ResultMessage, SystemMessage

from cairn import bundle, canary, dispatch
from cairn.substrate import Substrate
import cairn.worker as worker

ROLE = "canary"
TEMPLATE_NAME = "canary_echo"
TEMPLATE = "Return exactly the content of the first handed node, with no surrounding text."


class CaptureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        self.requests = []
        self.requests_lock = threading.Lock()
        super().__init__(address, CaptureHandler)


class CaptureHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if urlsplit(self.path).path != "/v1/messages":
            self._send(404, b'{"type":"error","error":{"type":"not_found_error"}}', "application/json")
            return
        with self.server.requests_lock:
            self.server.requests.append(body)
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, b'{"type":"error","error":{"type":"invalid_request_error"}}', "application/json")
            return
        if not isinstance(payload, dict):
            self._send(400, b'{"type":"error","error":{"type":"invalid_request_error"}}', "application/json")
            return
        if payload.get("stream"):
            self._send(200, _synthetic_stream(payload), "text/event-stream")
        else:
            self._send(200, _synthetic_message(payload), "application/json")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _synthetic_message(payload):
    return json.dumps(
        {
            "id": "msg_local_capture_only",
            "type": "message",
            "role": "assistant",
            "model": payload.get("model", "local-capture"),
            "content": [{"type": "text", "text": "LOCAL_CAPTURE_ONLY"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
        separators=(",", ":"),
    ).encode()


def _synthetic_stream(payload):
    message = json.loads(_synthetic_message(payload))
    start = {
        "type": "message_start",
        "message": {
            **message,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 0},
        },
    }
    events = (
        ("message_start", start),
        (
            "content_block_start",
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "LOCAL_CAPTURE_ONLY"}},
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    )
    return b"".join(
        f"event: {name}\ndata: {json.dumps(value, separators=(',', ':'))}\n\n".encode()
        for name, value in events
    )


def _sdk_details():
    cli_path = Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
    cli_version = subprocess.run([str(cli_path), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    sdk_version = importlib.metadata.version("claude-agent-sdk")
    if sdk_version != worker.SDK_VERSION or cli_version.split()[0] != worker.CLI_VERSION:
        raise RuntimeError(f"canary requires SDK {worker.SDK_VERSION} and CLI {worker.CLI_VERSION}")
    return {
        "sdk_version": sdk_version,
        "cli_version": cli_version.split()[0],
        "cli_path": str(cli_path),
        "cli_sha256": hashlib.sha256(cli_path.read_bytes()).hexdigest(),
    }


def _arm_options(prepared, project, endpoint, *, settings_enabled):
    options = canary.options_for(prepared, project, settings_enabled=settings_enabled)
    env = dict(options.env or {})
    env.update(
        {
            "ANTHROPIC_API_KEY": "canary-capture-dummy",
            "ANTHROPIC_BASE_URL": endpoint,
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        }
    )
    return replace(options, env=env)


async def _query(prepared, options):
    init_messages = []
    result_messages = []
    async with asyncio.timeout(45):
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prepared.prompt)
            async for message in client.receive_response():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    init_messages.append(message.data)
                elif isinstance(message, ResultMessage):
                    result_messages.append(
                        {"subtype": message.subtype, "is_error": message.is_error, "result": message.result}
                    )
    return {"init_messages": init_messages, "result_messages": result_messages}


def _classify_arm(bodies, plantings, control):
    decoded = [body.decode("utf-8", errors="replace") for body in bodies]
    valid_json = True
    for body in bodies:
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            valid_json = False
            continue
        if not isinstance(payload, dict):
            valid_json = False
    text = "\n".join(decoded)
    found = canary.found(text, plantings)
    return {
        "request_count": len(bodies),
        "source_tokens_found": list(found),
        "source_tokens_absent": [p["source"] for p in plantings if p["source"] not in found],
        "handed_control_detected": control in text,
        "valid_json": valid_json,
    }


def _persist_bodies(sub, directory, arm, bodies):
    entries = []
    for index, body in enumerate(bodies, start=1):
        name = f"{arm}-request-{index:03d}.body"
        (directory / name).write_bytes(body)
        entries.append(
            {
                "file": name,
                "blob_hash": sub.put_blob(body),
                "byte_length": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    return entries


def _source_sha():
    digest = hashlib.sha256()
    for path in (Path(worker.__file__), Path(dispatch.__file__), Path(canary.__file__), Path(__file__)):
        digest.update(path.name.encode())
        digest.update(b"\x00")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _record_if_complete(
    sub,
    *,
    no_errors,
    required_source_checks,
    plantings,
    observed,
    control_observed,
    handed_control_detected,
    sdk_version,
    cli_version,
):
    if not no_errors or not all(required_source_checks.values()):
        return None
    return canary.record(
        sub,
        form=canary.FORM_REQUEST_BYTES,
        plantings=plantings,
        observed=observed,
        control_observed=control_observed,
        handed_control_detected=handed_control_detected,
        sdk_version=sdk_version,
        cli_version=cli_version,
    )


def _bundle(directory):
    source = directory / "source"
    source.mkdir()
    (source / "worker_roles.json").write_text(
        json.dumps(
            {
                ROLE: {
                    "template": TEMPLATE_NAME,
                    "tools": [],
                    "model": "claude-haiku-4-5-20251001",
                    "max_turns": 1,
                    "timeout_s": 180,
                }
            }
        )
    )
    (source / "role_templates.json").write_text(json.dumps({TEMPLATE_NAME: TEMPLATE}))
    path, pin = directory / "bundle.sqlite", directory / "bundle.pin"
    bundle.build(source, path)
    pin.write_text(bundle.bundle_hash(bundle.read_rows(path)) + "\n")
    return bundle.GateBundle.open(path, pin)


def run(*, seed=None, artifact_dir=None):
    directory = Path(tempfile.mkdtemp(prefix="cairn-canary-")) if artifact_dir is None else Path(artifact_dir)
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise FileExistsError(f"canary artifact directory is not empty: {directory}")
    home = directory / "home"
    project = directory / "project"
    home.mkdir()
    project.mkdir()
    seed = directory.name if seed is None else str(seed)
    plantings = canary.plant(project, home=home, seed=seed)
    subprocess.run([shutil.which("git"), "init", "-q", str(project)], check=True)
    control = canary.control_token(seed)
    sdk_details = _sdk_details()
    gate_bundle = _bundle(directory)
    with Substrate.open(directory / "substrate.sqlite") as sub:
        node = sub.put_node("worker_input", control.encode())
        prepared = dispatch._prepare(sub, gate_bundle, role=ROLE, node_ids=(node,))
        server = CaptureServer(("127.0.0.1", 0))
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        host, port = server.server_address
        if host != "127.0.0.1":
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
            raise RuntimeError("canary capture server did not bind to loopback")
        endpoint = f"http://127.0.0.1:{port}"
        arms = {"dispatch": False, "control": True}
        arm_results = {}
        arm_bodies = {}
        try:
            with canary.config_dir(home):
                for name, settings_enabled in arms.items():
                    with server.requests_lock:
                        start = len(server.requests)
                    query_result = {"init_messages": [], "result_messages": []}
                    error_type = None
                    try:
                        options = _arm_options(
                            prepared,
                            project,
                            endpoint,
                            settings_enabled=settings_enabled,
                        )
                        query_result = asyncio.run(_query(prepared, options))
                    except Exception as exc:
                        error_type = type(exc).__name__
                    with server.requests_lock:
                        captured = list(server.requests[start:])
                    arm_bodies[name] = captured
                    request_observation = _classify_arm(captured, plantings, control)
                    init_file = f"{name}-init.json"
                    result_file = f"{name}-result.json"
                    (directory / init_file).write_text(
                        json.dumps(query_result["init_messages"], sort_keys=True, indent=2) + "\n"
                    )
                    (directory / result_file).write_text(
                        json.dumps(query_result["result_messages"], sort_keys=True, indent=2) + "\n"
                    )
                    arm_results[name] = {
                        **request_observation,
                        "error_type": error_type,
                        "init_file": init_file,
                        "result_file": result_file,
                        "synthetic_response_completed": any(
                            result["subtype"] == "success"
                            and not result["is_error"]
                            and result["result"] == "LOCAL_CAPTURE_ONLY"
                            for result in query_result["result_messages"]
                        ),
                    }
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
        request_bodies = {
            name: _persist_bodies(sub, directory, name, bodies) for name, bodies in arm_bodies.items()
        }
        observed = "\n".join(body.decode("utf-8", errors="replace") for body in arm_bodies["dispatch"])
        control_observed = "\n".join(body.decode("utf-8", errors="replace") for body in arm_bodies["control"])
        required_source_checks = {
            source: source in arm_results["control"]["source_tokens_found"] for source in canary.SOURCES
        }
        dispatch_clean = (
            arm_results["dispatch"]["request_count"] > 0
            and arm_results["dispatch"]["valid_json"]
            and arm_results["dispatch"]["source_tokens_found"] == []
            and arm_results["dispatch"]["handed_control_detected"]
        )
        no_errors = all(
            result["request_count"] > 0
            and result["valid_json"]
            and result["error_type"] is None
            and result["synthetic_response_completed"]
            for result in arm_results.values()
        )
        capture_complete = no_errors and all(required_source_checks.values())
        record = _record_if_complete(
            sub,
            no_errors=no_errors,
            required_source_checks=required_source_checks,
            plantings=plantings,
            observed=observed,
            control_observed=control_observed,
            handed_control_detected=arm_results["dispatch"]["handed_control_detected"],
            sdk_version=sdk_details["sdk_version"],
            cli_version=sdk_details["cli_version"],
        )
        accepted = (
            record is not None
            and record.verdict == canary.PASS
            and dispatch_clean
            and all(required_source_checks.values())
            and no_errors
        )
        source_sha = subprocess.run(
            [shutil.which("git"), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        summary = {
            "artifact_directory": str(directory),
            "home": str(home),
            "project": str(project),
            "seed": seed,
            "source_sha": source_sha,
            "source_sha256": _source_sha(),
            "sdk_cli": sdk_details,
            "endpoint": endpoint,
            "plantings": list(plantings),
            "request_bodies": request_bodies,
            "arms": arm_results,
            "required_source_checks": required_source_checks,
            "capture_complete": capture_complete,
            "dispatch_clean_with_handed_control": dispatch_clean,
            "all_arms_completed_synthetic_response": no_errors,
            "canary_record": None if record is None else record.as_dict(),
            "canary_record_hash": None if record is None else record.hash,
            "substrate": str(directory / "substrate.sqlite"),
            "scope": "The capture measures serialized CLI request context; LOCAL_CAPTURE_ONLY is synthetic and establishes no model or provider behavior.",
            "exit_code": 0 if accepted else 2,
        }
        (directory / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
        return summary


def main():
    summary = run()
    print(json.dumps(summary, sort_keys=True))
    return summary["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
