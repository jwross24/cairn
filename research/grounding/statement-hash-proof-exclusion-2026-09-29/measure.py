import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_project_modules():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import factories

    from cairn import bundle, lean, solutionchecks

    return factories, bundle, lean, solutionchecks


factories, bundle, lean, solutionchecks = load_project_modules()


def frame(data, start, limit):
    if not 0 <= start <= limit <= len(data):
        raise ValueError("invalid-frame-boundary")
    colon = data.find(b":", start, limit)
    if colon < 0:
        raise ValueError("truncated-frame-header")
    digits = data[start:colon]
    if not digits or any(byte < 48 or byte > 57 for byte in digits):
        raise ValueError("invalid-frame-length")
    if len(digits) > 1 and digits[0] == 48:
        raise ValueError("noncanonical-frame-length")
    end = colon + 1 + int(digits)
    if end > limit:
        raise ValueError("truncated-frame")
    return colon + 1, end


def framed_fields(data, start, limit):
    while start < limit:
        frame_start = start
        payload_start, end = frame(data, start, limit)
        yield frame_start, payload_start, end
        start = end
    if start != limit:
        raise ValueError("trailing-frame-bytes")


def node(data, start, limit):
    tag_start, tag_end = frame(data, start, limit)
    payload_start, payload_end = frame(data, tag_end, limit)
    if payload_end != limit:
        raise ValueError("trailing-node-bytes")
    return data[tag_start:tag_end], payload_start, payload_end


def canonical_stats(data):
    tag, start, end = node(data, 0, len(data))
    if tag != b"cairn.formal-statement.v1":
        raise ValueError("wrong-canonical-root")
    outer = list(framed_fields(data, start, end))
    if len(outer) != 2:
        raise ValueError("wrong-canonical-field-count")
    targets_tag, targets_start, targets_end = node(data, outer[0][1], outer[0][2])
    closure_tag, closure_start, closure_end = node(data, outer[1][1], outer[1][2])
    if targets_tag != b"targets" or closure_tag != b"closure":
        raise ValueError("wrong-canonical-fields")
    root_count = sum(1 for _ in framed_fields(data, targets_start, targets_end))
    records = list(framed_fields(data, closure_start, closure_end))
    return root_count, len(records), max((stop - payload_start for _, payload_start, stop in records), default=0)


def verify_truncated_frame_refusal():
    try:
        frame(b"3:ab", 0, 4)
    except ValueError as exc:
        if str(exc) != "truncated-frame":
            raise
    else:
        raise AssertionError("truncated-frame-accepted")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def statement_input(item):
    if item in ("curve", "curve_plus"):
        formal = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"
        if item == "curve_plus":
            formal = formal.replace("W.Δ = W.Δ", "W.Δ + 0 = W.Δ")
        return formal, "challenge_curve", 4
    if item == "dlp":
        formal = (
            "theorem cairn_dlp_iff {F : Type} [Field F] [DecidableEq F] {W : WeierstrassCurve.Affine F}\n"
            "    (P Q : W.Point) : (∃ k : \u2124, k • P = Q) ↔ Q ∈ AddSubgroup.zmultiples P := by\n"
            "  sorry\n"
        )
        return formal, "cairn_dlp_iff", 61
    formal = (
        "theorem cairn_finite_point {F : Type} [Field F] [Finite F] (W : WeierstrassCurve.Affine F) :\n"
        "    Finite W.Point := by\n"
        "  sorry\n"
    )
    return formal, "cairn_finite_point", 61


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--item", choices=("dlp", "curve", "curve_plus", "finite"), default="dlp")
    args = parser.parse_args()
    verify_truncated_frame_refusal()
    root = Path(args.output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=False)

    source_path = lean.STATEMENT_HASHER_PATH
    source_start = source_path.read_bytes()
    source_sha_start = hashlib.sha256(source_start).hexdigest()
    formal, theorem, seed = statement_input(args.item)
    statement = factories.claim_statement(seed=seed, formal_source=formal)
    source_input = {
        "item": args.item,
        "theorem_names": [theorem],
        "factory_seed": seed,
        "claim_statement_hash": statement.hash,
        "formal_source": formal,
        "formal_source_sha256": hashlib.sha256(formal.encode()).hexdigest(),
    }
    write_json(root / "source-input.json", source_input)

    gate_path = root / "gate.sqlite"
    pin_path = root / "gate.pin"
    bundle.build(REPO_ROOT / "bundle", gate_path)
    bundle.write_pin(gate_path, pin_path)
    gate = bundle.GateBundle.open(gate_path, pin_path)
    if gate.raw(lean.STATEMENT_HASHER_KIND) != source_start:
        raise RuntimeError("built-gate-hasher-differs-from-source-snapshot")
    (root / "statement-hasher.lean").write_bytes(source_start)

    original_digest = lean.statement_digest
    observed = {}

    def capture(result):
        wire = result.stdout.encode("utf-8")
        (root / "canonical-output.json").write_bytes(wire)
        digest = original_digest(result)
        encoded = json.loads(result.stdout)["canonical_hex"]
        canonical = bytes.fromhex(encoded)
        root_count, closure_count, largest_record_bytes = canonical_stats(canonical)
        (root / "canonical.bin").write_bytes(canonical)
        observed.update(
            wire_bytes=len(wire),
            wire_sha256=hashlib.sha256(wire).hexdigest(),
            canonical_bytes=len(canonical),
            canonical_sha256=hashlib.sha256(canonical).hexdigest(),
            root_count=root_count,
            closure_constants=closure_count,
            largest_record_bytes=largest_record_bytes,
            formal_statement_hash=digest,
        )
        return digest

    lean.statement_digest = capture
    started = time.monotonic()
    try:
        prepared = solutionchecks.prepare_dev(
            gate,
            statement,
            (theorem,),
            root=root / "challenge",
            dependency_project=lean.PROJECT_DIR,
        )
    except BaseException as exc:
        elapsed = time.monotonic() - started
        end_source = source_path.read_bytes()
        stable = end_source == source_start
        write_json(
            root / "measurement.json",
            {
                "status": "failed",
                "item": args.item,
                "hasher_sha256_start": source_sha_start,
                "hasher_sha256_end": hashlib.sha256(end_source).hexdigest(),
                "hasher_source_stable": stable,
                "timeout_seconds": lean.DEFAULT_TIMEOUT_S,
                "prepare_wall_seconds": elapsed,
                "error_type": type(exc).__name__,
                "error": str(exc),
                **observed,
            },
        )
        if not stable:
            raise RuntimeError("hasher-source-changed-during-measurement") from exc
        raise
    finally:
        lean.statement_digest = original_digest

    end_source = source_path.read_bytes()
    if end_source != source_start:
        raise RuntimeError("hasher-source-changed-during-measurement")
    if observed.get("formal_statement_hash") != prepared.formal_statement_hash:
        raise RuntimeError("captured-hash-differs-from-preparation-result")
    measurement = {
        "status": "prepared",
        "item": args.item,
        "gate_bundle_hash": gate.hash,
        "gate_pin_hash": gate.pin_hash,
        "lean_toolchain": gate.lean["toolchain"],
        "mathlib_revision": gate.lean["mathlib_rev"],
        "hasher_sha256": source_sha_start,
        "hasher_sha256_start": source_sha_start,
        "hasher_sha256_end": hashlib.sha256(end_source).hexdigest(),
        "hasher_source_stable": True,
        "timeout_seconds": lean.DEFAULT_TIMEOUT_S,
        "prepare_wall_seconds": time.monotonic() - started,
        **observed,
    }
    write_json(root / "measurement.json", measurement)
    print(json.dumps(measurement, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
