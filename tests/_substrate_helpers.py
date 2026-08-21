from cairn.substrate import Substrate

IDENTITY_A = {
    "interface_version": "toy_curve/1",
    "implementation_revision": "aa" * 32,
    "tool_digests": {"gp": "11" * 32},
    "container_digest": "cc" * 32,
    "numeric_profile": None,
}
IDENTITY_B = {**IDENTITY_A, "implementation_revision": "bb" * 32}
ENV_MANIFEST_HASH = "ee" * 32
TRANSCRIPT_HASH = "77" * 32
SELFTEST_SUMMARY = {"corpus_origins": [], "randomized_arm": True, "cross_check": None, "pass": 4, "floor": 4}


def recipe(seed=1, *, skill_identity_hash="aa" * 32, salt="", inputs=None):
    return {
        "skill_identity_hash": skill_identity_hash,
        "inputs": inputs or {},
        "seed": seed,
        "tool_versions": {"gp": "2.17.4"},
        "container_digest": "cc" * 32,
        "salt": salt,
    }


def open_writer(tmp_path, name="substrate.sqlite"):
    return Substrate.open(tmp_path / name, role="writer")


def store_artifacts(sub, payloads):
    return {name: (sub.put_blob(data), len(data)) for name, data in payloads.items()}


def launch(sub, recipe_key, status="OK", payloads=None, *, skip_cache_lookup=False, replay_grade="Replayable"):
    attempt_id = sub.start_attempt(recipe_key, replay_grade=replay_grade, skip_cache_lookup=skip_cache_lookup)
    manifest = None
    if payloads is not None:
        artifacts = store_artifacts(sub, payloads)
        manifest = sub.put_output_manifest(artifacts, recipe_key=recipe_key)
    sub.close_attempt(attempt_id, status, output_manifest_hash=manifest)
    return attempt_id, manifest
