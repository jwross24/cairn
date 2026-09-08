"""Ground the dispatch canary against the installed SDK and CLI.

    uv run python research/grounding/probe_dispatch_canary.py

Plants one token in each settings source, dispatches the canary role twice — once
under the dispatch envelope and once with the settings sources enabled as a control —
and writes the grounding record the dispatch gate reads.
"""

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from cairn import bundle, canary, dispatch
from cairn.substrate import Substrate

ROLE = "canary"
TEMPLATE_NAME = "canary_echo"
TEMPLATE = "Return exactly the content of the first handed node, with no surrounding text."


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


def main():
    directory = Path(tempfile.mkdtemp(prefix="cairn-canary-"))
    root = directory / "tree"
    root.mkdir()
    seed = directory.name
    plantings = canary.plant(root, seed=seed)
    subprocess.run([shutil.which("git"), "init", "-q", str(root)], check=True)
    control = canary.control_token(seed)
    gate_bundle = _bundle(directory)
    with Substrate.open(directory / "substrate.sqlite") as sub:
        node = sub.put_node("worker_input", control.encode())
        prepared = dispatch._prepare(sub, gate_bundle, role=ROLE, node_ids=(node,))
        with canary.config_dir(root):
            observed = asyncio.run(canary.observe(prepared, root, settings_enabled=False))
            control_observed = asyncio.run(canary.observe(prepared, root, settings_enabled=True))
        record = canary.record(
            sub,
            form=canary.FORM_ECHO,
            plantings=plantings,
            observed=observed,
            control_observed=control_observed,
            handed_control_detected=control in observed,
        )
        (directory / "observed.txt").write_text(observed)
        (directory / "control.txt").write_text(control_observed)
        print(
            json.dumps(
                {
                    "artifact_directory": str(directory),
                    "record": record.as_dict(),
                    "substrate": str(directory / "substrate.sqlite"),
                },
                sort_keys=True,
            )
        )
    return 0 if record.verdict == canary.PASS else 2


if __name__ == "__main__":
    sys.exit(main())
