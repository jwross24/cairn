import pytest

from cairn import yank

H = "aa" * 32
OTHER = "bb" * 32


def recipe_row(seed=1, *, revision=H, tool_versions_hash="tv", container_digest="cc" * 32, salt=""):
    return {
        "skill_identity_hash": revision,
        "seed": seed,
        "tool_versions_hash": tool_versions_hash,
        "container_digest": container_digest,
        "salt": salt,
    }


def fields(inputs=None):
    return {"inputs": inputs or {}}


def test_the_default_reach_is_the_whole_revision():
    reach = yank.validate_reach(yank.default_reach(H), H)
    assert reach == {"skill_identity_hash": H}
    assert not yank.narrower(reach)
    assert yank.covers(reach, recipe_row(seed=99, salt="s"), fields())
    assert not yank.covers(reach, recipe_row(revision=OTHER), fields())


def test_reach_json_round_trips_in_key_order():
    reach = {"skill_identity_hash": H, "seed": [1, 3]}
    text = yank.reach_json(reach)
    assert text == '{"seed":[1,3],"skill_identity_hash":"' + H + '"}'
    assert yank.reach_from_json(text) == reach
    with pytest.raises(yank.MalformedReach, match="not JSON"):
        yank.reach_from_json("{")


@pytest.mark.parametrize(
    ("reach", "match"),
    [
        ("all", "must be a mapping"),
        ({}, "must name the yanked revision"),
        ({"skill_identity_hash": OTHER}, "must name the yanked revision"),
        ({"skill_identity_hash": H, "bits": [0, 50]}, "names no recipe-key field bits"),
        ({"skill_identity_hash": H, "seed": "1"}, "expected an int or"),
        ({"skill_identity_hash": H, "seed": True}, "neither an int nor a range"),
        ({"skill_identity_hash": H, "seed": [3, 1]}, "is empty"),
        ({"skill_identity_hash": H, "seed": [1, 2, 3]}, "expected an int or"),
        ({"skill_identity_hash": H, "inputs": {}}, "non-empty mapping"),
        ({"skill_identity_hash": H, "inputs": {"curve": []}}, "non-empty list of blob hashes"),
        ({"skill_identity_hash": H, "inputs": {"curve": [""]}}, "non-empty list of blob hashes"),
        ({"skill_identity_hash": H, "salt": ""}, "expected a non-empty str"),
        ({"skill_identity_hash": H, "container_digest": 3}, "expected a non-empty str"),
    ],
)
def test_a_malformed_reach_is_refused_before_anything_is_written(reach, match):
    with pytest.raises(yank.MalformedReach, match=match):
        yank.validate_reach(reach, H)


def test_a_seed_range_covers_exactly_the_seeds_inside_it():
    reach = yank.validate_reach({"skill_identity_hash": H, "seed": [2, 4]}, H)
    assert yank.narrower(reach)
    assert [yank.covers(reach, recipe_row(seed=s), fields()) for s in (1, 2, 3, 4, 5)] == [
        False,
        True,
        True,
        True,
        False,
    ]
    single = yank.validate_reach({"skill_identity_hash": H, "seed": 3}, H)
    assert [yank.covers(single, recipe_row(seed=s), fields()) for s in (2, 3, 4)] == [False, True, False]


def test_equality_fields_narrow_by_exact_match():
    reach = yank.validate_reach({"skill_identity_hash": H, "salt": "yank-1", "tool_versions_hash": "tv"}, H)
    assert yank.covers(reach, recipe_row(salt="yank-1"), fields())
    assert not yank.covers(reach, recipe_row(salt=""), fields())
    assert not yank.covers(reach, recipe_row(salt="yank-1", tool_versions_hash="other"), fields())


def test_an_inputs_reach_is_membership_of_the_recipes_blob_hash():
    reach = yank.validate_reach({"skill_identity_hash": H, "inputs": {"curve": ["11" * 32, "22" * 32]}}, H)
    assert yank.covers(reach, recipe_row(), fields({"curve": ("22" * 32, 9)}))
    assert not yank.covers(reach, recipe_row(), fields({"curve": ("33" * 32, 9)}))
    assert not yank.covers(reach, recipe_row(), fields({"other": ("11" * 32, 9)}))


def test_reach_fields_are_exactly_the_recipe_key_fields():
    assert yank.REACH_FIELDS == (
        "skill_identity_hash",
        "seed",
        "inputs",
        "tool_versions_hash",
        "container_digest",
        "salt",
    )
    assert yank.KINDS == ("gate_verdict", "human_path")
