import json
import pathlib
import subprocess
import sys

P = pathlib.Path(sys.argv[1])
ARENA = pathlib.Path(sys.argv[2])
OUT = P / "out"
AXIOMS = ["propext", "Classical.choice", "Quot.sound"]
BINS = {"pin": P / "nanoda/pin/target/release/nanoda_bin", "head": P / "nanoda/head/target/release/nanoda_bin"}
LIMIT = 50_000_000


def rows():
    merged = {}
    for name in ("results.jsonl", "dir_results.jsonl", "pr_results.jsonl"):
        for line in (OUT / name).read_text().splitlines():
            r = json.loads(line)
            r.setdefault("outcome", "reject")
            merged[r["name"]] = r
    return merged


def export_path(r):
    local = OUT / f"{r['name']}.ndjson"
    if local.exists():
        return local
    guess = ARENA / (r["name"].replace("__", "/") + ".ndjson")
    return guess if guess.exists() else None


def verdict(binary, path, name):
    config = {
        "use_stdin": False,
        "export_file_path": str(path),
        "permitted_axioms": AXIOMS,
        "unpermitted_axiom_hard_error": True,
        "nat_extension": True,
        "string_extension": True,
    }
    cfg = OUT / f"{name}.host.json"
    cfg.write_text(json.dumps(config))
    try:
        r = subprocess.run([str(binary), str(cfg)], capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    text = r.stdout + r.stderr
    if r.returncode == 0:
        return "ACCEPT", text
    if "Declined" in text:
        return "DECLINED", text
    if text.startswith("Error:") or "\nError:" in text:
        return "CONFIG", text
    return "KERNEL-REFUSE", text


table = []
for name, r in sorted(rows().items()):
    path = export_path(r)
    if path is None or path.stat().st_size > LIMIT:
        continue
    pin, _ = verdict(BINS["pin"], path, name)
    head, text = verdict(BINS["head"], path, name)
    image = r.get("nanoda")
    if image is None and "nanoda_rc" in r:
        image = "ACCEPT" if r["nanoda_rc"] == 0 else "NONZERO"
    table.append({"name": name, "outcome": r["outcome"], "image_pin": image, "native_pin": pin, "native_head": head, "head_text": text[-260:]})

(OUT / "nanoda_compare.json").write_text(json.dumps(table, indent=1))
parity = [t["name"] for t in table if (t["image_pin"] == "ACCEPT") != (t["native_pin"] == "ACCEPT")]
print("rows", len(table), "parity-mismatch", parity)
changed = [t for t in table if (t["native_pin"] == "ACCEPT") != (t["native_head"] == "ACCEPT")]
for t in changed:
    print("CHANGED", t["name"].ljust(44), t["outcome"].ljust(7), t["native_pin"], "->", t["native_head"], repr(t["head_text"][:150]))
rej = [t for t in table if t["outcome"] == "reject"]
print("reject rows", len(rej), "head accepts:", [t["name"] for t in rej if t["native_head"] == "ACCEPT"])
print("head on accept controls:", [(t["name"], t["native_head"]) for t in table if t["outcome"] == "accept"])
