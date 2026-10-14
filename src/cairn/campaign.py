import argparse
import json
import math
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from cairn import bundle, canon, claims, exits, hunt, justify, keys, repro, runner, substrate
from cairn.cli import GLOBAL_DEFAULTS
from cairn.profile import Evaluation

ROLES = ("control_must_survive", "plant_must_be_killed", "question")
EXPECTED_VERDICTS = {"control_must_survive": "SURVIVED", "plant_must_be_killed": "KILLED", "question": None}


class CampaignRefused(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


@dataclass(frozen=True)
class PreparedStatement:
    spec: dict
    statement: claims.ClaimStatement
    hypothesis: claims.HypothesisObject
    plan: hunt.HuntPlan


def _object(value, fields, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    unknown = set(value) - fields
    missing = fields - set(value)
    if unknown or missing:
        raise ValueError(f"{name}: unknown keys {sorted(unknown)}; missing keys {sorted(missing)}")


def _text(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _size_axis(statement):
    axes = statement["distribution"]
    if len(axes) == 1:
        return next(iter(axes))
    scope = statement["scope"]
    matching = [axis for axis in axes if scope["param_ranges"].get(axis) == scope["size_interval"]]
    if len(matching) != 1:
        raise ValueError("multi-axis statement requires one scope parameter range matching size_interval")
    return matching[0]


def parse_spec(value):
    _object(
        value,
        {"family", "method_identity", "module_dir", "tool_versions", "executor", "verifier", "statements"},
        "spec",
    )
    _text(value["family"], "family")
    _text(value["module_dir"], "module_dir")
    canon.encode(keys.METHOD_IDENTITY, value["method_identity"])
    versions = value["tool_versions"]
    if not isinstance(versions, dict):
        raise ValueError("tool_versions must be an object")
    for name, version in versions.items():
        _text(name, "tool name")
        _text(version, f"tool_versions[{name!r}]")
    for name in ("executor", "verifier"):
        program = value[name]
        fields = {"module", "sources", "digest", "expected_wall_s"}
        if "skill" in program or "skill_identity_hash" in program:
            fields |= {"skill", "skill_identity_hash"}
        _object(program, fields, name)
        if "skill" in program:
            from cairn import selftest_skills

            if program["skill"] not in selftest_skills.NAMES:
                raise ValueError(f"{name}.skill must name a registered self-test skill")
            if (
                not isinstance(program["skill_identity_hash"], str)
                or re.fullmatch(r"[0-9a-f]{64}", program["skill_identity_hash"]) is None
            ):
                raise ValueError(f"{name}.skill_identity_hash must be 64 lowercase hex characters")
        if (
            not isinstance(program["module"], str)
            or re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", program["module"]) is None
        ):
            raise ValueError(f"{name}.module must name a Python module")
        sources = program["sources"]
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"{name}.sources must be a non-empty list")
        for source in sources:
            _text(source, f"{name}.sources")
            path = Path(source)
            if path.is_absolute() or ".." in path.parts or path.as_posix() != source or source == ".":
                raise ValueError(f"{name}.sources must contain normalized relative file paths")
        if len(set(sources)) != len(sources):
            raise ValueError(f"{name}.sources must not repeat a path")
        if not isinstance(program["digest"], str) or re.fullmatch(r"[0-9a-f]{64}", program["digest"]) is None:
            raise ValueError(f"{name}.digest must be 64 lowercase hex characters")
        wall = program["expected_wall_s"]
        if isinstance(wall, bool) or not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall <= 0:
            raise ValueError(f"{name}.expected_wall_s must be finite and positive")
    statements = value["statements"]
    if not isinstance(statements, list) or not statements:
        raise ValueError("statements must be a non-empty list")
    claim_ids = set()
    for index, statement in enumerate(statements):
        name = f"statements[{index}]"
        _object(
            statement,
            {"role", "claim_id", "informal", "scope", "quantities", "predicate", "distribution", "trial_count"},
            name,
        )
        if statement["role"] not in ROLES:
            raise ValueError(f"{name}.role must be one of {ROLES}")
        _text(statement["claim_id"], f"{name}.claim_id")
        if statement["claim_id"] in claim_ids:
            raise ValueError(f"duplicate claim_id {statement['claim_id']!r}")
        claim_ids.add(statement["claim_id"])
        _text(statement["informal"], f"{name}.informal")
        canon.encode(claims.SCOPE, statement["scope"])
        canon.encode(claims.QUANTITIES, statement["quantities"])
        scope = statement["scope"]
        if scope["target_family"] != value["family"]:
            raise ValueError(f"{name}.scope.target_family differs from family")
        interval = scope["size_interval"]
        if len(interval) != 2 or interval[0] > interval[1]:
            raise ValueError(f"{name}.scope.size_interval must be an inclusive integer range")
        if not isinstance(statement["predicate"], dict):
            raise ValueError(f"{name}.predicate must be an object")
        json.dumps(statement["predicate"], allow_nan=False)
        hunt.Distribution(statement["distribution"])
    prepare_statements(value)
    return value


def source_digest(module_dir, sources):
    framed = bytearray()
    root = Path(module_dir).resolve()
    for relative in sources:
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"source {relative!r} is outside module_dir")
        name = relative.encode("utf-8")
        content = path.read_bytes()
        framed.extend(len(name).to_bytes(8, "big"))
        framed.extend(name)
        framed.extend(len(content).to_bytes(8, "big"))
        framed.extend(content)
    return substrate.blob_hash(bytes(framed))


def check_digests(spec):
    for name in ("executor", "verifier"):
        program = spec[name]
        actual = source_digest(spec["module_dir"], program["sources"])
        if actual != program["digest"]:
            raise CampaignRefused(f"{name} digest differs from the spec")
        if "skill" in program:
            _check_skill_program(spec, name)


def _check_skill_program(spec, name):
    from cairn import selftest_skills

    program = spec[name]
    module = selftest_skills.module_for(program["skill"])
    allowed = {module.__name__, getattr(module, "HUNT_MODULE", module.__name__)}
    if program["module"] not in allowed:
        raise CampaignRefused(f"{name} module is outside the named skill's entry points")
    root = Path(module.REPO_ROOT).resolve()
    if Path(spec["module_dir"]).resolve() != root / "src":
        raise CampaignRefused(f"{name} module_dir differs from the installed skill's source root")
    expected = {(root / relative).resolve() for relative in module.IDENTITY_SOURCES}
    actual = {(Path(spec["module_dir"]) / relative).resolve() for relative in program["sources"]}
    launched = (Path(spec["module_dir"]) / (program["module"].replace(".", "/") + ".py")).resolve()
    if actual != expected or launched not in expected:
        raise CampaignRefused(f"{name} sources do not match the named skill's identity sources")
    if module.skill_identity_hash(root) != program["skill_identity_hash"]:
        raise CampaignRefused(f"{name} skill identity differs from the spec")


def _program_identity(program):
    return program.get("skill_identity_hash", program["digest"])


def check_verifier_standing(sub, spec):
    if "skill" not in spec["verifier"]:
        return
    verifier = repro.Verifier(repro.SKILL_VERIFIER, _program_identity(spec["verifier"]))
    grade, reason = repro.owner_grade(sub, _program_identity(spec["executor"]), verifier)
    if grade != repro.VERIFIABLE:
        hint = ""
        if reason == "verifier-uncertified":
            hint = f"; `cairn selftest {spec['verifier']['skill']}` against this --db certifies it"
        raise CampaignRefused(f"verifier standing is {grade} ({reason}) before any draw{hint}")


def prepare_statements(spec):
    prepared = []
    for row in spec["statements"]:
        statement = claims.ClaimStatement(row["claim_id"], 1, row["informal"], row["scope"], row["quantities"])
        distribution = hunt.Distribution(row["distribution"])
        hypothesis = claims.HypothesisObject(
            spec["family"],
            {"statement_hash": statement.hash, "predicate": claims.to_json(row["predicate"]), "role": row["role"]},
            spec["method_identity"],
            {axis: list(bounds) for axis, bounds in distribution.ranges.items()},
            distribution.hash,
            statement.hash,
        )
        plan = hunt.HuntPlan(
            statement.hash,
            hypothesis.hash,
            distribution,
            row["trial_count"],
            distribution.ranges,
            size_axis=_size_axis(row),
            method_identity=spec["method_identity"],
            target_family=spec["family"],
            assumption_set=frozenset(row["scope"]["assumption_set"]),
            executor_identity=_program_identity(spec["executor"]),
            verifier_identity=_program_identity(spec["verifier"]),
        )
        prepared.append(PreparedStatement(row, statement, hypothesis, plan))
    return prepared


def statement_document(prepared):
    return {
        "role": prepared.spec["role"],
        "claim_id": prepared.statement.claim_id,
        "statement_hash": prepared.statement.hash,
        "hypothesis_hash": prepared.hypothesis.hash,
        "distribution_hash": prepared.plan.distribution.hash,
        "plan_hash": prepared.plan.hash,
        "trial_count": prepared.plan.trial_count,
        "expected_verdict": EXPECTED_VERDICTS[prepared.spec["role"]],
    }


def plan_document(spec, prepared):
    return {
        "family": spec["family"],
        "executor_identity": _program_identity(spec["executor"]),
        "verifier_identity": _program_identity(spec["verifier"]),
        "statements": [statement_document(row) for row in prepared],
    }


def _trial_document(context, predicate):
    return {
        "statement_hash": context.plan.statement_hash,
        "plan_hash": context.plan.hash,
        "run_id": context.run_id,
        "trial": context.trial,
        "point": dict(context.point),
        "seed": context.seed,
        "input_blob_hash": context.input_blob_hash,
        "predicate": predicate,
    }


def run_campaign(spec, prepared, *, db, bundle_path, pin, attest, scratch):
    from cairn import env

    check_digests(spec)
    gate_bundle = bundle.GateBundle.open(bundle_path, pin)
    container_digest = keys.env_manifest_digest(env.manifest())
    tool_digests = {
        name: substrate.blob_hash(version.encode("utf-8")) for name, version in spec["tool_versions"].items()
    }
    report = plan_document(spec, [])
    report.update(bundle_hash=gate_bundle.hash, container_digest=container_digest)
    with substrate.Substrate.open(db) as sub:
        check_verifier_standing(sub, spec)
        for row in prepared:
            claims.write_claim_statement(sub, row.statement)
            claims.write_hypothesis_object(sub, row.hypothesis)

        def launch(context, name, inputs, document):
            check_digests(spec)
            program = spec[name]
            recipe = {
                "skill_identity_hash": _program_identity(program),
                "inputs": inputs,
                "seed": context.seed,
                "tool_versions": tool_digests,
                "container_digest": container_digest,
                "salt": f"hunt/{context.run_id}/{context.trial}/{name}",
            }
            wall = program["expected_wall_s"]
            child_env = {"PYTHONPATH": str(Path(spec["module_dir"]).resolve())}
            if "skill" in program:
                child_env["PYTHONSAFEPATH"] = "1"
            return runner.launch(
                sub,
                program["module"],
                recipe,
                bundle_hash=gate_bundle.hash,
                evaluation=Evaluation(wall, wall, wall),
                ceiling_multiplier=4,
                tool_digests=tool_digests,
                scratch_root=scratch,
                skip_cache_lookup=True,
                do_not_cache=True,
                env_extra=child_env,
                stdin_document=document,
                attest_path=attest,
            )

        for role in ROLES:
            for row in prepared:
                if row.spec["role"] != role:
                    continue
                predicate = row.spec["predicate"]

                def executor(context, predicate=predicate):
                    return launch(
                        context,
                        "executor",
                        {"hunt_input": (context.input_blob_hash, context.input_blob_size)},
                        _trial_document(context, predicate),
                    )

                def verifier(context, execution, predicate=predicate):
                    document = _trial_document(context, predicate)
                    document["executor_output_digest"] = execution.output_json_hash
                    return launch(
                        context,
                        "verifier",
                        {
                            "hunt_input": (context.input_blob_hash, context.input_blob_size),
                            "executor_output": (
                                execution.output_json_hash,
                                len(sub.get_blob(execution.output_json_hash)),
                            ),
                        },
                        document,
                    )

                result = hunt.run_hunt(sub, row.plan, executor, verifier, attest_path=attest)
                derivation = (
                    justify.derive_tag(sub, row.statement.hash, attest)
                    if result.verdict == "SURVIVED"
                    else result.judgment
                )
                entry = statement_document(row)
                entry.update(
                    verdict=result.verdict,
                    run_hash=result.run_hash,
                    evidence_hash=result.evidence_hash,
                    ledger_hash=result.ledger_hash,
                    derived_tag=None if derivation is None else derivation.tag,
                )
                report["statements"].append(entry)
                expected = EXPECTED_VERDICTS[role]
                if (expected is not None and result.verdict != expected) or result.verdict == "INCOMPLETE":
                    report["stopped"] = {"role": role, "claim_id": row.statement.claim_id, "verdict": result.verdict}
                    return report, exits.GATE_REFUSED
    return report, exits.OK


def main(argv=None):
    parser = ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Plan statements only; certification and runtime readiness are not checked.",
    )
    parser.add_argument("--scratch", type=Path)
    for name in ("db", "bundle", "pin", "attest"):
        parser.add_argument(f"--{name}", default=GLOBAL_DEFAULTS[name], type=Path)
    try:
        args = parser.parse_args(argv)
        if args.scratch is None and not args.plan_only:
            raise ValueError("--scratch is required unless --plan-only")
        spec = parse_spec(json.loads(args.spec.read_text()))
        prepared = prepare_statements(spec)
    except (ValueError, TypeError, OSError, hunt.HuntError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return exits.USER_INPUT
    try:
        check_digests(spec)
        if args.plan_only:
            report, code = plan_document(spec, prepared), exits.OK
            report.update(certification="not_checked", runtime_readiness="not_checked")
        else:
            report, code = run_campaign(
                spec,
                prepared,
                db=args.db,
                bundle_path=args.bundle,
                pin=args.pin,
                attest=args.attest,
                scratch=args.scratch,
            )
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        if code == exits.GATE_REFUSED:
            stopped = report["stopped"]
            print(f"refused: {stopped['role']} {stopped['claim_id']} returned {stopped['verdict']}", file=sys.stderr)
        return code
    except (CampaignRefused, bundle.BundleError, substrate.SubstrateError, sqlite3.Error, OSError, ValueError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return exits.GATE_REFUSED


if __name__ == "__main__":
    sys.exit(main())
