import re
import shlex
from pathlib import Path

from cairn import cli

ROOT = Path(__file__).resolve().parents[2]


def _handbook_sequence():
    section = cli.robot_docs_text().split("## Canonical operator sequence", 1)[1].split("\n## ", 1)[0]
    commands = []
    values = {}
    for line in section.splitlines():
        match = re.match(r"\d+\. (cairn .+?)\s+\(", line)
        if match is None:
            continue
        tokens = shlex.split(match[1])
        for index, token in enumerate(tokens):
            if token.startswith("--"):
                value = tokens[index + 1]
                if value == "...":
                    tokens[index + 1] = values[token]
                else:
                    values[token] = value
        commands.append(tokens)
    assert len(commands) == 6
    return commands


def test_development_deployment_commands_equal_the_handbook_sequence_in_order():
    text = (ROOT / "docs" / "development.md").read_text()
    deployment = text.split("## Deployment\n", 1)[1].split("\n## ", 1)[0]
    commands = [shlex.split(line)[2:] for line in deployment.splitlines() if line.startswith("uv run cairn ")]
    assert commands == _handbook_sequence()


def test_readme_deploy_names_the_handbook_sequence_in_order_and_links_to_full_flags():
    text = (ROOT / "README.md").read_text()
    deployment = text.split("### Deploy\n", 1)[1].split("\n## ", 1)[0]
    names = [" ".join(tokens).split(" --", 1)[0] for tokens in _handbook_sequence()]
    positions = [deployment.index(f"`{name}`") for name in names]
    assert positions == sorted(positions)
    assert "docs/development.md#deployment" in deployment
    assert "git-ignored" in deployment and "operator-owned" in deployment
