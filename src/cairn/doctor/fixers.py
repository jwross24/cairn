import os
from dataclasses import dataclass
from pathlib import Path

from cairn import log
from cairn.doctor import detectors, mutate

lg = log.get("doctor.fix")

FIXERS = (
    ("F-modes", "restore the pin to 0444+uappnd and the attestation file to 0644+uappnd"),
    ("F-dirs", "create a missing deploy/ or var/ and add .doctor/ and var/ to .gitignore"),
)


@dataclass(frozen=True)
class Action:
    fixer: str
    path: str
    op: mutate.Op
    describe: str
    because: tuple

    def as_dict(self):
        return {
            "fixer": self.fixer,
            "path": self.path,
            "op": self.op.kind,
            "describe": self.describe,
            "because": list(self.because),
        }


def _modes_actions(findings):
    by_path = {}
    for finding in findings:
        if finding.fixer != detectors.F_MODES:
            continue
        entry = by_path.setdefault(finding.target, {"want": (finding.want_mode, finding.want_flags), "why": []})
        entry["why"].append(finding.id)
    actions = []
    for path in sorted(by_path):
        mode, flags = by_path[path]["want"]
        actions.append(
            Action(
                detectors.F_MODES,
                path,
                mutate.Op(mutate.MODES, mode=mode, flags=flags),
                f"chflags nouappnd {path}; chmod {mode:04o} {path}; chflags uappnd {path}",
                tuple(by_path[path]["why"]),
            )
        )
    return actions


def _gitignore_bytes(path):
    if not Path(path).is_file():
        return b"".join(f"{entry}\n".encode() for entry in detectors.GITIGNORE_ENTRIES)
    text = Path(path).read_text()
    lines = {line.strip() for line in text.splitlines()}
    missing = [entry for entry in detectors.GITIGNORE_ENTRIES if entry not in lines]
    if text and not text.endswith("\n"):
        text += "\n"
    return (text + "".join(f"{entry}\n" for entry in missing)).encode()


def _dirs_actions(findings):
    actions = []
    for finding in findings:
        if finding.fixer != detectors.F_DIRS:
            continue
        if finding.id == "D-dirs/gitignore":
            actions.append(
                Action(
                    detectors.F_DIRS,
                    finding.target,
                    mutate.Op(mutate.WRITE, data=_gitignore_bytes(finding.target)),
                    f"append the missing entries to {finding.target}",
                    (finding.id,),
                )
            )
        else:
            actions.append(
                Action(
                    detectors.F_DIRS,
                    finding.target,
                    mutate.Op(mutate.MKDIR, mode=0o755),
                    f"mkdir {finding.target}",
                    (finding.id,),
                )
            )
    return actions


def plan(findings):
    actions = _dirs_actions(findings) + _modes_actions(findings)
    lg.info("plan", actions=[a.as_dict() for a in actions])
    return actions


def apply(run, actions):
    applied = []
    for action in actions:
        if action.op.kind == mutate.MODES and not os.path.lexists(action.path):
            raise mutate.Refused(f"{action.path} is missing; creating a pin or attestation file is an operator act")
        applied.append(mutate.mutate(run, action.path, action.op))
    return applied
