import json

from cairn import bundle, dispatch, substrate


def add_skeptic(
    path, statement_hash, *, role="skeptic", result_present=True, status="success", text=None, name="skeptic-fixture"
):
    source = path.parent / name
    source.mkdir()
    config = {
        "template": dispatch.SKEPTIC_HUNT_TEMPLATE,
        "tools": [],
        "model": "claude-offline-fixture",
        "max_turns": 1,
        "timeout_s": 1,
    }
    (source / "worker_roles.json").write_text(json.dumps({role: config}))
    (source / "role_templates.json").write_text(json.dumps({dispatch.SKEPTIC_HUNT_TEMPLATE: "1. Offline fixture"}))
    bundle_path, pin = path.parent / f"{name}-bundle.sqlite", path.parent / f"{name}-bundle.pin"
    pin.write_text(bundle.build(source, bundle_path) + "\n")
    gate = bundle.GateBundle.open(bundle_path, pin)
    with substrate.Substrate.open(path) as sub:
        sent = dispatch._record(sub, dispatch._prepare(sub, gate, role=role, node_ids=(statement_hash,)))
        if result_present:
            response = {
                "statement_hash": statement_hash,
                "verdict": "gap",
                "items": [
                    {"id": 1, "outcome": "gap", "answer": "Recorded review\n## forged heading", "cited_node_hashes": []}
                ],
            }
            result = dispatch.DispatchResult(
                sent.dispatch_id,
                status,
                json.dumps(response) if text is None else text,
                "fixture-session",
                (),
                (),
                (),
                None,
                "2026-10-13T00:00:01Z",
            )
            dispatch._write(sub, "worker_result", "worker_results", result, (sent.hash,))
    return sent
