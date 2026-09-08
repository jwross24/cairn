import argparse
import difflib
import hashlib
import json
import os
import tempfile
from pathlib import Path

from cairn import lean


def emit(label, result):
    print(json.dumps({"label": label, **result.__dict__}, sort_keys=True), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparator", type=Path, required=True)
    args = parser.parse_args()
    comparator = args.comparator.resolve()
    root = Path(tempfile.mkdtemp(prefix="cairn-f4-reference-"))
    pins = lean.source_pins()
    lean.assert_pinned(pins)
    os.environ["COMPARATOR_LANDRUN"] = str(comparator / "scripts" / "fake-landrun.sh")
    exporter = comparator / ".lake" / "packages" / "lean4export" / ".lake" / "build" / "bin" / "lean4export"
    os.environ["COMPARATOR_LEAN4EXPORT"] = str(exporter)
    binary = comparator / ".lake" / "build" / "bin" / "comparator"
    source = "def bound : Nat := 3\ntheorem target (n : Nat) (h : n < bound) : n < bound := by sorry\n"
    pairs = {"fresh": source, "comment": "-- one comment\n" + source,
             "unused": source + "def unused : Nat := 17\n",
             "hypothesis": source.replace("(h : n < bound)", "(h : n ≤ bound)"),
             "definition": source.replace(": Nat := 3", ": Nat := 4")}
    exports = []
    for label, candidate in pairs.items():
        project = root / label
        project.mkdir()
        (project / "lean-toolchain").write_text(pins["toolchain"] + "\n")
        (project / "lakefile.toml").write_text(
            'name = "differential_probe"\n\n[[lean_lib]]\nname = "Challenge"\n\n[[lean_lib]]\nname = "Solution"\n\n[[lean_lib]]\nname = "Raw"\n'
        )
        (project / "Challenge.lean").write_text(source)
        (project / "Solution.lean").write_text(candidate)
        config = {"challenge_module": "Challenge", "solution_module": "Solution", "theorem_names": ["target"],
                  "permitted_axioms": ["propext", "Classical.choice", "Quot.sound", "sorryAx"], "enable_nanoda": False}
        (project / "config.json").write_text(json.dumps(config))
        print(json.dumps({"pair": label, "diff": "".join(difflib.unified_diff(source.splitlines(True), candidate.splitlines(True))),
                          "reference_only_permitted_axioms": config["permitted_axioms"]}), flush=True)
        result = emit(label, lean.run(pins, "lake", ["env", str(binary), "config.json"], cwd=project))
        semantic = label in ("hypothesis", "definition")
        assert (result.rc == 0) == (not semantic), result
        expected = "do not match" if label == "hypothesis" else "does not match" if semantic else "Your solution is okay!"
        assert expected in result.stdout + result.stderr
        if label in ("fresh", "comment"):
            (project / "Raw.lean").write_text(candidate)
            lean.require_success(lean.run(pins, "lake", ["build", "Raw"], cwd=project))
            exported = lean.require_success(lean.run(pins, "lake", ["env", str(exporter), "Raw", "--", "target"], cwd=project))
            data = exported.stdout.encode()
            (project / "Raw.export.jsonl").write_bytes(data)
            exports.append(data)
            print(json.dumps({"raw_export": label, "module": "Raw", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}), flush=True)
    assert exports[0] != exports[1]
    print(json.dumps({"artifacts": str(root), "verdict": "pass"}), flush=True)


if __name__ == "__main__":
    main()
