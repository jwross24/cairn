import json
import sys
from pathlib import Path

import blake3

from cairn import env, keys, pari
from cairn.profile import CostProfile, Production, SizeCost, Verification

CROSS_CHECKS: tuple[dict, ...] = (
    {"axis": "algorithm", "independent_range": {"bits": [10, 20]}, "seam": "skills.multi_axis.algorithm_sum"},
    {"axis": "implementation", "independent_range": {"bits": [30, 40]}, "seam": "skills.multi_axis.implementation_sum"},
)
INTERFACE_VERSION = "multi_axis/1"
COST_PROFILE = CostProfile(
    tier=0,
    production=Production(
        model="constant",
        per_size={bits: SizeCost(1.0, 0.0, 1.0e-3, 0.05) for bits in (20, 30, 40, 60)},
    ),
    verification=Verification(grade="Replayable", cost_model="same_as_production"),
    source="fixture: fixed arithmetic comparisons",
)


def algorithm_sum(bits, seed):
    return sum((bits, seed))


def implementation_sum(bits, seed):
    return bits - (-seed)


def run(bits, seed, fault="", fault_axis="implementation"):
    checks = []
    for declaration in CROSS_CHECKS:
        axis = declaration["axis"]
        low, high = declaration["independent_range"]["bits"]
        if low <= bits <= high:
            if fault == "inert" and axis == fault_axis:
                result = "agree"
            else:
                oracle = algorithm_sum if axis == "algorithm" else implementation_sum
                result = "agree" if oracle(bits, seed) == bits + seed else "disagree"
        else:
            result = "agree" if fault == "outside" and axis == fault_axis else "untested"
        record = {"axis": axis, "independent_range": declaration["independent_range"], "result": result}
        if fault == "output_range" and axis == fault_axis:
            record["independent_range"] = {"bits": [0, 60]}
        if fault != "output_missing" or axis != fault_axis:
            checks.append(record)
    return {
        "bits": bits,
        "seed": seed,
        "cross_check": checks,
        "status": "DISAGREE" if any(record["result"] == "disagree" for record in checks) else "OK",
    }


def identity_bundle():
    versions = pari.pari_versions()
    return {
        "interface_version": INTERFACE_VERSION,
        "implementation_revision": blake3.blake3(Path(__file__).read_bytes()).hexdigest(),
        "tool_digests": {
            "gp_binary_sha256": env.gp_binary_sha256(),
            "cypari2": versions["cypari2"],
            "libpari": versions["libpari"],
        },
        "container_digest": keys.env_manifest_digest(env.manifest()),
        "numeric_profile": None,
    }


def certify(sub, fault="", fault_axis="implementation", extra_key="passed"):
    records = []
    for declaration in CROSS_CHECKS:
        record = {
            "axis": declaration["axis"],
            "independent_range": {name: list(interval) for name, interval in declaration["independent_range"].items()},
        }
        if fault == "ledger_extra" and declaration["axis"] == fault_axis:
            record[extra_key] = True
        if fault == "ledger_range" and declaration["axis"] == fault_axis:
            record["independent_range"] = {"bits": [0, 60]}
        if fault != "ledger_missing" or declaration["axis"] != fault_axis:
            records.append(record)
    summary = {"cross_check": records}
    identity = identity_bundle()
    identity_hash = sub.put_identity_bundle(identity)
    transcript = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
    sub.put_certificate(
        identity_hash, blake3.blake3(transcript).hexdigest(), keys.env_manifest_digest(env.manifest()), summary
    )
    return {"summary": summary, "identity_bundle_hash": identity_hash}


def main(stdin=None, stdout=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    inputs = json.loads(stdin.read())
    document = run(inputs["bits"], inputs["seed"], inputs.get("fault", ""), inputs.get("fault_axis", "implementation"))
    stdout.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
