import json

BEAD = "cairn-m0-e0s.16"


def theater(*findings):
    summary = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0, "NOTE": 0}
    for finding in findings:
        summary[finding["severity"]] += 1
    return {"bead_id": BEAD, "scanned_files": [], "findings": list(findings), "summary": summary}


def write_pass(tmp_path, findings):
    pass_dir = tmp_path / "passes" / "2026-08-26T16-29-01Z"
    bead_dir = pass_dir / "beads" / BEAD
    bead_dir.mkdir(parents=True)
    (bead_dir / "theater.json").write_text(json.dumps(theater(*findings), indent=2) + "\n")
    (bead_dir / "spec.json").write_text(json.dumps({"bead_id": BEAD, "items": []}))
    (bead_dir / "show.json").write_text(json.dumps({"id": BEAD, "status": "closed"}))
    return pass_dir, bead_dir
