import itertools
import sqlite3

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule, run_state_machine_as_test

from cairn import keys, substrate

from _substrate_helpers import open_writer, recipe
from mutants import substrate_mutants

RECIPES = ("r0", "r1", "r2")
BLOBS = {"b0": b"blob-0", "b1": b"blob-1", "b2": b"blob-2", "b3": b"blob-3"}
MANIFESTS = {"m0": {"a": "b0"}, "m1": {"a": "b1", "b": "b3"}, "m2": {"a": "b2", "b": "b3"}}
STATEFUL_SETTINGS = settings(max_examples=200, stateful_step_count=50, deadline=None, database=None)


def build_machine(base_dir):
    counter = itertools.count()

    class SubstrateServeMachine(RuleBasedStateMachine):
        attempts = Bundle("attempts")

        def __init__(self):
            super().__init__()
            self.dir = base_dir / f"example-{next(counter)}"
            self.dir.mkdir()
            self.sub = open_writer(self.dir)
            assert self.sub.journal_mode() == "wal"
            self.recipe_keys = {}
            self.pending_do_not_cache = set()
            self.do_not_cache = set()
            self.model = {name: [] for name in RECIPES}
            self.present = set()

        def teardown(self):
            self.sub.close()

        def _recipe_key(self, name):
            if name not in self.recipe_keys:
                flag = name in self.pending_do_not_cache
                self.recipe_keys[name] = self.sub.put_recipe(recipe(RECIPES.index(name)), do_not_cache=flag)
                if flag:
                    self.do_not_cache.add(name)
            return self.recipe_keys[name]

        def _entry(self, ref):
            name, attempt_id = ref
            return name, next(e for e in self.model[name] if e["attempt_id"] == attempt_id)

        @rule(target=attempts, name=st.sampled_from(RECIPES), manifest=st.sampled_from(sorted(MANIFESTS)))
        def launch(self, name, manifest):
            key = self._recipe_key(name)
            artifacts = {}
            for artifact, blob in MANIFESTS[manifest].items():
                artifacts[artifact] = (self.sub.put_blob(BLOBS[blob]), len(BLOBS[blob]))
                self.present.add(blob)
            attempt_id = self.sub.start_attempt(key)
            manifest_hash = self.sub.put_output_manifest(artifacts, recipe_key=key)
            self.sub.close_attempt(attempt_id, "OK", output_manifest_hash=manifest_hash)
            self.model[name].append({"attempt_id": attempt_id, "status": "OK", "disowned": False, "inadmissible": False, "manifest": manifest, "manifest_hash": manifest_hash})
            return (name, attempt_id)

        @rule(target=attempts, name=st.sampled_from(RECIPES), manifest=st.sampled_from(sorted(MANIFESTS)))
        def fail_launch(self, name, manifest):
            key = self._recipe_key(name)
            artifacts = {}
            for artifact, blob in MANIFESTS[manifest].items():
                artifacts[artifact] = (self.sub.put_blob(BLOBS[blob]), len(BLOBS[blob]))
                self.present.add(blob)
            attempt_id = self.sub.start_attempt(key)
            manifest_hash = self.sub.put_output_manifest(artifacts, recipe_key=key)
            self.sub.close_attempt(attempt_id, "FAIL", output_manifest_hash=manifest_hash)
            self.model[name].append({"attempt_id": attempt_id, "status": "FAIL", "disowned": False, "inadmissible": False, "manifest": manifest, "manifest_hash": manifest_hash})
            return (name, attempt_id)

        @rule(ref=attempts)
        def disown(self, ref):
            _, entry = self._entry(ref)
            if entry["disowned"]:
                with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                    self.sub.disown(entry["attempt_id"])
                return
            self.sub.disown(entry["attempt_id"])
            entry["disowned"] = True

        @rule(ref=attempts)
        def mark_inadmissible(self, ref):
            _, entry = self._entry(ref)
            if entry["inadmissible"]:
                with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                    self.sub.mark_inadmissible(entry["attempt_id"])
                return
            self.sub.mark_inadmissible(entry["attempt_id"])
            entry["inadmissible"] = True

        @rule(name=st.sampled_from(RECIPES))
        def set_do_not_cache(self, name):
            if name in self.recipe_keys:
                with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                    self.sub.conn.execute("UPDATE recipes SET do_not_cache = 1 WHERE recipe_key = ?", (self.recipe_keys[name],))
                return
            self.pending_do_not_cache.add(name)

        @rule(blob=st.sampled_from(sorted(BLOBS)))
        def drop_blob(self, blob):
            self.sub.conn.execute("DELETE FROM blobs WHERE hash = ?", (substrate.blob_hash(BLOBS[blob]),))
            self.present.discard(blob)

        @rule(name=st.sampled_from(RECIPES))
        def serve(self, name):
            self._check(name)

        @invariant()
        def serve_agrees_with_model(self):
            for name in RECIPES:
                self._check(name)

        def _eligible(self, name):
            if name in self.do_not_cache:
                return []
            return [
                e
                for e in self.model[name]
                if e["status"] == "OK" and not e["disowned"] and not e["inadmissible"] and all(b in self.present for b in MANIFESTS[e["manifest"]].values())
            ]

        def _check(self, name):
            key = self.recipe_keys.get(name) or keys.recipe_key(recipe(RECIPES.index(name)))
            served = self.sub.serve(key)
            eligible = self._eligible(name)
            if served is None:
                assert eligible == [], f"{name}: serve returned None with eligible attempts {[e['attempt_id'] for e in eligible]}"
                return
            by_id = {e["attempt_id"]: e for e in eligible}
            assert served.attempt_id in by_id, f"{name}: served ineligible attempt {served.attempt_id}; model {self.model[name]}; present {sorted(self.present)}"
            assert served.output_manifest_hash == by_id[served.attempt_id]["manifest_hash"]
            assert served.attempt_id == eligible[-1]["attempt_id"], f"{name}: served {served.attempt_id}, most recent eligible is {eligible[-1]['attempt_id']}"

    return SubstrateServeMachine


def run_machine(tmp_path):
    run_state_machine_as_test(build_machine(tmp_path), settings=STATEFUL_SETTINGS)


def test_serve_agrees_with_shadow_model_under_launch_disown_loss_interleavings(tmp_path):
    run_machine(tmp_path)


@pytest.mark.parametrize("name", sorted(substrate_mutants.ALL))
def test_mutant_is_killed(tmp_path, name):
    with substrate_mutants.ALL[name](), pytest.raises(AssertionError, match="served ineligible attempt"):
        run_machine(tmp_path)
