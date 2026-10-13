import argparse
import json
import os
import stat
import sys
from pathlib import Path

from cairn import attest, bundle, exits, keys, log, substrate


class DeploymentRefused(Exception):
    def __init__(self, stage, error, retained):
        super().__init__(error)
        self.stage = stage
        self.retained = retained


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def prepare(src_dir, directory):
    destination = Path(directory).absolute()
    paths = {
        "bundle": destination / "gate-bundle.sqlite",
        "pin": destination / "gate-bundle.pin",
        "attest": destination / "attestations.log",
    }
    created = False
    stage = "destination"
    try:
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"destination {destination} exists")
        stage = "preflight"
        objects = bundle.source_objects(src_dir)
        planned_hash = bundle.bundle_hash(bundle.rows_for(objects))
        target = keys.hypothesis_key(objects["gate_plan"]["fixtures"]["waiver_hypothesis"])
        canonical = attest.waiver_canonical(attest.fixture_waiver(target))
        stage = "create"
        destination.mkdir(mode=0o700)
        created = True
        stage = "build"
        built_hash = bundle.build(src_dir, paths["bundle"])
        if built_hash != planned_hash:
            raise ValueError("built bundle hash differs from preflight source hash")
        stage = "pin"
        if bundle.write_pin(paths["bundle"], paths["pin"]) != planned_hash:
            raise ValueError("pin hash differs from preflight source hash")
        stage = "bundle_readback"
        gate = bundle.GateBundle.open(paths["bundle"], paths["pin"])
        if gate.hash != planned_hash or gate.waiver_target() != target:
            raise ValueError("bundle readback differs from preflight sources")
        stage = "attest"
        offset, _ = attest.init(paths["attest"], target)
        stage = "readback"
        if offset != 0 or paths["attest"].read_bytes() != attest.frame(canonical):
            raise ValueError("attestation differs from the fixture waiver at offset 0")
        for path in (paths["bundle"], paths["pin"]):
            if stat.S_IMODE(path.stat().st_mode) != 0o444:
                raise ValueError(f"{path} is not read-only")
        if hasattr(os, "chflags"):
            for path in (paths["pin"], paths["attest"]):
                if not path.stat().st_flags & stat.UF_APPEND:
                    raise ValueError(f"{path} is not append-only")
        return {
            "status": "ready",
            **{name: str(path) for name, path in paths.items()},
            "bundle_hash": planned_hash,
            "waiver_offset": offset,
            "waiver_digest": substrate.blob_hash(canonical),
        }
    except Exception as exc:
        retained = []
        if created:
            retained = [str(destination), *(str(path) for path in paths.values() if path.exists() or path.is_symlink())]
        raise DeploymentRefused(stage, str(exc), retained) from exc


def main(argv=None):
    parser = ArgumentParser(prog="python -m cairn.deployment")
    parser.add_argument("--src", default=bundle.DEFAULT_SRC, type=Path)
    parser.add_argument("--directory", required=True, type=Path)
    try:
        args = parser.parse_args(argv)
    except ValueError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return exits.USER_INPUT
    log.configure()
    try:
        document = prepare(args.src, args.directory)
    except DeploymentRefused as exc:
        print(
            json.dumps({"status": "refused", "stage": exc.stage, "error": str(exc), "retained": exc.retained}),
            file=sys.stderr,
        )
        return exits.GATE_REFUSED
    print(json.dumps(document, sort_keys=True))
    return exits.OK


if __name__ == "__main__":
    sys.exit(main())
