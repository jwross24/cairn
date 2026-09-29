from cairn import status, substrate


def test_missing_substrate_is_absent_and_empty_substrate_is_zero(tmp_path):
    paths = {
        "db_path": tmp_path / "missing.sqlite",
        "bundle_path": tmp_path / "missing-bundle.sqlite",
        "pin_path": tmp_path / "missing.pin",
        "attest_path": tmp_path / "missing-attestations.log",
    }
    missing = status.document(**paths)
    assert missing["skills"]["state"] == "absent"
    assert missing["claims"]["state"] == "absent"
    assert missing["gate_runs"]["state"] == "absent"
    assert missing["gate_plan"]["state"] == "absent"
    assert missing["human_queue"]["state"] == "absent"
    assert missing["tiers"]["state"] == "absent"

    with substrate.Substrate.open(paths["db_path"]):
        pass

    empty = status.document(**paths)
    assert empty["skills"] == {"state": "present", "revisions": []}
    assert empty["claims"]["state"] == "present"
    assert empty["claims"]["total"] == 0
    assert set(empty["claims"]["by_status"].values()) == {0}
    assert empty["claims"]["by_calibration"]["untagged"] == 0
    assert empty["gate_runs"] == {"state": "present", "limit": 10, "runs": []}
    assert empty["gate_plan"]["state"] == "absent"
    assert empty["human_queue"] == {"state": "present", "depth": 0}
    assert not paths["bundle_path"].exists()
    assert not paths["pin_path"].exists()
    assert not paths["attest_path"].exists()


def test_affordance_for_missing_statement_input_has_no_exit_code(tmp_path):
    snapshot, _ = status._bundle_snapshot(tmp_path / "missing.sqlite", tmp_path / "missing.pin")

    affordances, requires_input = status._affordances(
        snapshot, "bundle.sqlite", "bundle.pin", "substrate.sqlite", "attestations.log", 10
    )

    assert requires_input == [
        {
            "command": "cairn justify",
            "arguments": ["--statement"],
            "reason": "a claim statement hash is required",
        }
    ]
    assert all("exit_code" not in affordance for affordance in requires_input)


def test_malformed_bundle_is_unavailable_not_absent(tmp_path):
    bundle_path = tmp_path / "bundle.sqlite"
    pin_path = tmp_path / "bundle.pin"
    bundle_path.write_bytes(b"not a sqlite database")
    pin_path.write_text("pin\n")

    snapshot, _ = status._bundle_snapshot(bundle_path, pin_path)
    document = status.document(
        db_path=tmp_path / "missing-substrate.sqlite",
        bundle_path=bundle_path,
        pin_path=pin_path,
        attest_path=tmp_path / "missing-attestations.log",
    )

    assert snapshot["state"] == "unavailable"
    assert document["gate_plan"]["state"] == "unavailable"
    assert document["tiers"]["state"] == "unavailable"
