import argparse
import json
import os
import tempfile
from pathlib import Path

from cairn import lean


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparator", type=Path, required=True)
    comparator = parser.parse_args().comparator.resolve()
    root = Path(tempfile.mkdtemp(prefix="cairn-solution-precondition-"))
    pins = lean.source_pins()
    lean.assert_pinned(pins)
    (root / "lean-toolchain").write_text(pins["toolchain"] + "\n")
    (root / "lakefile.toml").write_text(
        'name = "solution_precondition"\n\n[[lean_lib]]\nname = "Challenge"\n\n[[lean_lib]]\nname = "Solution"\n'
    )
    (root / "Challenge.lean").write_text("theorem target : True := by sorry\n")
    source = 'import Lean\nrun_elab Lean.logInfo "CAIRN_ELABORATOR_EXECUTED"\ntheorem target : True := True.intro\n'
    (root / "Solution.lean").write_text(source)
    (root / "config.json").write_text(json.dumps({
        "challenge_module": "Challenge", "solution_module": "Solution", "theorem_names": ["target"],
        "permitted_axioms": pins["permitted_axioms"], "enable_nanoda": False,
    }))
    os.environ["COMPARATOR_LANDRUN"] = str(comparator / "scripts" / "fake-landrun.sh")
    os.environ["COMPARATOR_LEAN4EXPORT"] = str(comparator / ".lake/packages/lean4export/.lake/build/bin/lean4export")
    result = lean.run(pins, "lake", ["env", str(comparator / ".lake/build/bin/comparator"), "config.json"], cwd=root)
    print(json.dumps({"root": str(root), "solution": source, **result.__dict__}), flush=True)
    assert result.rc == 0
    assert "CAIRN_ELABORATOR_EXECUTED" in result.stdout
    assert "Your solution is okay!" in result.stdout


if __name__ == "__main__":
    main()
