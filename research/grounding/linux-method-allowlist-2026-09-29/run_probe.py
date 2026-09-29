import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKER = "/usr/local/bin/docker"
SOURCE_PATHS = (
    "bundle/Containerfile",
    "bundle/container.json",
    "bundle/allow_lists.json",
    "src/cairn/allowlist.py",
    "src/cairn/runner.py",
    "src/cairn/ladder.py",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def command(argv, timeout=30):
    start = time.monotonic()
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return {
        "argv": argv,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed_s": time.monotonic() - start,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary-directory", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect", action="append", default=[])
    args = parser.parse_args()
    git = shutil.which("git")
    go = shutil.which("go")
    if git is None or go is None:
        parser.error("git and go must be available for provenance receipts")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image):
        parser.error("--image must be a full immutable image ID")
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha must be a full commit SHA")
    binary_dir = args.binary_directory.resolve()
    paths = [binary_dir / name for name in ("probe", "backend", "undeclared")]
    if set(binary_dir.iterdir()) != set(paths) or any(not path.is_file() or path.is_symlink() for path in paths):
        parser.error("binary directory must contain exactly three regular, separately copied executables")
    binaries = [path.read_bytes() for path in paths]
    if any(data != binaries[0] for data in binaries):
        parser.error("binary copies must have identical bytes")
    if len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) != 3:
        parser.error("binary copies must have distinct inodes")
    data = binaries[0]
    if data[:6] != b"\x7fELF\x02\x01" or int.from_bytes(data[18:20], "little") != 183:
        parser.error("probe must be a 64-bit little-endian Linux arm64 ELF")
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error("run output must be outside the checkout")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "source_sha": args.source_sha,
        "source_files": {},
        "driver_sha256": digest(Path(__file__).read_bytes()),
        "probe_source_sha256": digest(Path(__file__).with_name("probe.go").read_bytes()),
        "binary_sha256": digest(data),
        "image_id": args.image,
        "commands": [],
        "no_claim": "Standalone candidate observations do not establish production method enforcement.",
    }
    for path in SOURCE_PATHS:
        source = subprocess.check_output([git, "show", f"{args.source_sha}:{path}"], cwd=ROOT, timeout=30)
        manifest["source_files"][path] = digest(source)
    for argv in (
        [DOCKER, "version", "--format", "{{.Client.Version}} {{.Server.Version}}"],
        [DOCKER, "info", "--format", "{{.KernelVersion}} {{.OperatingSystem}}"],
        [DOCKER, "image", "inspect", args.image, "--format", "{{.Id}} {{.Architecture}} {{.Os}}"],
        [go, "version", "-m", str(paths[0])],
    ):
        receipt = command(argv)
        manifest["commands"].append(receipt)
        if receipt["returncode"]:
            (output / "receipt.json").write_text(json.dumps(manifest, indent=2) + "\n")
            raise SystemExit(receipt["returncode"])
    inspected = manifest["commands"][2]["stdout"].split()
    if inspected != [args.image, "arm64", "linux"]:
        (output / "receipt.json").write_text(json.dumps(manifest, indent=2) + "\n")
        raise ValueError(f"image inspection differs from the requested Linux arm64 image: {inspected}")
    name = f"cairn-hcl-{uuid.uuid4().hex}"
    argv = [
        DOCKER,
        "run",
        "--rm",
        "--name",
        name,
        "--memory=6g",
        "--memory-swap=6g",
        "--network=none",
        "--mount",
        f"type=bind,source={binary_dir},target=/probe,readonly",
        args.image,
        "/probe/probe",
        "harness",
        "--landrun",
        "/usr/local/bin/landrun",
    ]
    for expected in args.expect:
        argv.extend(["--expect", expected])
    try:
        receipt = command(argv, timeout=180)
    except subprocess.TimeoutExpired as exc:
        stopped = command([DOCKER, "stop", "--time", "0", name])
        manifest["commands"].append(stopped)
        manifest["timeout"] = {"argv": argv, "seconds": exc.timeout}
        for label, value in (("stdout", exc.stdout), ("stderr", exc.stderr)):
            raw = value.decode(errors="replace") if isinstance(value, bytes) else value or ""
            (output / f"probe.{label}").write_text(raw)
        (output / "receipt.json").write_text(json.dumps(manifest, indent=2) + "\n")
        raise SystemExit(124) from None
    manifest["commands"].append(receipt)
    (output / "probe.stdout").write_text(receipt["stdout"])
    (output / "probe.stderr").write_text(receipt["stderr"])
    (output / "receipt.json").write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        document = json.loads(receipt["stdout"])
    except json.JSONDecodeError as exc:
        manifest["protocol_error"] = str(exc)
        (output / "receipt.json").write_text(json.dumps(manifest, indent=2) + "\n")
        raise SystemExit(receipt["returncode"] or 2) from None
    if not isinstance(document, dict):
        raise ValueError("probe output must be a JSON object")
    (output / "result.json").write_text(json.dumps(document, indent=2) + "\n")
    print(json.dumps({"output": str(output), "returncode": receipt["returncode"], "image": args.image}))
    raise SystemExit(receipt["returncode"])


if __name__ == "__main__":
    main()
