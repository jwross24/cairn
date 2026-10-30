import hashlib
import json
import pathlib
import shlex
import subprocess
import sys
import time

import yaml

CONTAINER = "p76j-probe"
ROOT = pathlib.Path(sys.argv[1])
WORK = pathlib.Path(sys.argv[2])
SELECT = sys.argv[3] if len(sys.argv) > 3 else "all"
OUT = WORK / "out"
LEAN4EXPORT = "/home/cairn/comparator/.lake/packages/lean4export/.lake/build/bin/lean4export"
PROBE = "/work/driver/.lake/build/bin/probe"
ENV = "export PATH=/home/cairn/lean/bin:/home/cairn/.elan/bin:/usr/local/bin:/usr/bin:/bin; "
AXIOMS = ["propext", "Classical.choice", "Quot.sound"]
TIMEOUT = 300


def sh(script, timeout=TIMEOUT + 60):
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c", ENV + script], capture_output=True, text=True, timeout=timeout
    )
    return r.returncode, (r.stdout + r.stderr)


def classify(rc):
    if rc == 0:
        return "ACCEPT"
    if rc == 124:
        return "TIMEOUT"
    if rc >= 128:
        return f"CRASH-{rc}"
    return "ERROR"


def official(export):
    rc, text = sh(f"timeout {TIMEOUT} {PROBE} {shlex.quote(export)}")
    if rc == 0 and text.startswith("ACCEPT"):
        return "ACCEPT", text
    if rc == 1 and text.startswith("REJECT"):
        return "REJECT", text
    if rc == 2:
        return "PARSE-FAIL", text
    return classify(rc) if rc != 0 else "ERROR", text


def nanoda(export, name):
    config = {
        "use_stdin": False,
        "export_file_path": export,
        "permitted_axioms": AXIOMS,
        "unpermitted_axiom_hard_error": True,
        "nat_extension": True,
        "string_extension": True,
    }
    (OUT / f"{name}.nanoda.json").write_text(json.dumps(config, separators=(",", ":")))
    rc, text = sh(f"timeout {TIMEOUT} /usr/local/bin/nanoda_bin /work/out/{shlex.quote(name)}.nanoda.json")
    if rc == 0:
        return "ACCEPT", text
    return (classify(rc) if rc == 124 or rc >= 128 else "NONZERO"), text


def build_lean(name, source, decls):
    project = shlex.quote(f"/work/lean/{name}")
    args = " ".join(shlex.quote(str(d)) for d in decls or [])
    tail = f" -- {args}" if args else ""
    script = (
        f"set -e; mkdir -p {project}; cd {project}; cp {shlex.quote(f'/arena/{source}')} Test.lean; "
        "echo leanprover/lean4:v4.34.0-rc1 > lean-toolchain; "
        "printf 'name = \"test\"\\n\\n[[lean_lib]]\\nname = \"Test\"\\n' > lakefile.toml; "
        f"timeout {TIMEOUT} lake build Test"
    )
    rc, text = sh(script)
    if rc != 0:
        return None, text
    export = f"/work/out/{name}.ndjson"
    rc, text2 = sh(f"cd {project} && timeout {TIMEOUT} lake env {LEAN4EXPORT} Test{tail} > {shlex.quote(export)}")
    return (export if rc == 0 else None), text + text2


def leanchecker(name):
    project = shlex.quote(f"/work/lean/{name}")
    rc, text = sh(f"cd {project} && timeout {TIMEOUT} lake env /home/cairn/lean/bin/leanchecker --fresh -v Test")
    return classify(rc) if rc == 0 or rc == 124 or rc >= 128 else "NONZERO", text


def load():
    items = []
    for y in sorted((ROOT / "tests").rglob("*.yaml")):
        d = yaml.safe_load(y.read_text())
        name = str(y.relative_to(ROOT / "tests"))[:-5].replace("/", "__")
        if not isinstance(d, dict) or d.get("outcome") not in ("reject", "accept", "either"):
            print("NO-OUTCOME", name, "multiple" if isinstance(d, dict) and d.get("multiple") else "unrecognized", flush=True)
            continue
        group = name.split("__")[0] if "__" in name else "top"
        sibling = y.with_suffix(".ndjson")
        file_key = d.get("file")
        leanfile = d.get("leanfile")
        if sibling.exists():
            source = ("ndjson", "/arena/" + str(sibling.relative_to(ROOT / "tests")))
        elif file_key:
            source = ("ndjson", "/arena/" + file_key.removeprefix("tests/"))
        elif leanfile:
            source = ("lean", leanfile.removeprefix("tests/"))
        else:
            print("NO-ROUTE", name, d["outcome"], "dir" if d.get("dir") else "url" if d.get("url") else "module", flush=True)
            continue
        keep = d["outcome"] == "reject" or (group != "perf" and d["outcome"] in ("accept", "either"))
        if keep:
            items.append({"name": name, "group": group, "outcome": d["outcome"], "source": source, "decls": d.get("export-decls")})
        else:
            print("NOT-SELECTED", name, d["outcome"], flush=True)
    return sorted(items, key=lambda i: (i["outcome"] != "reject", i["name"]))


def main():
    results = OUT / "results.jsonl"
    done = set()
    if results.exists():
        done = {json.loads(line)["name"] for line in results.read_text().splitlines()}
    items = load()
    print("selected", len(items), flush=True)
    for item in items:
        if item["name"] in done or (SELECT != "all" and SELECT not in item["name"]):
            continue
        start = time.time()
        rec = {k: item[k] for k in ("name", "group", "outcome")}
        kind, source = item["source"]
        rec["route"] = kind
        if kind == "lean":
            export, log = build_lean(item["name"], source, item["decls"])
            rec["build_log_tail"] = log[-600:]
            if export is None:
                rec["official"] = rec["nanoda"] = "BUILD-FAIL"
                rec["seconds"] = round(time.time() - start, 1)
                with results.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(item["name"].ljust(40), "BUILD-FAIL", flush=True)
                continue
            rec["leanchecker_fresh"], text = leanchecker(item["name"])
            rec["leanchecker_text"] = text[-500:]
        else:
            export = source
        host = export.replace("/work/", str(WORK) + "/") if export.startswith("/work/") else str(ROOT / "tests" / export.removeprefix("/arena/"))
        rec["export_sha256"] = hashlib.sha256(pathlib.Path(host).read_bytes()).hexdigest()
        rec["export_bytes"] = pathlib.Path(host).stat().st_size
        rec["official"], text = official(export)
        rec["official_text"] = text[-500:]
        rec["nanoda"], text = nanoda(export, item["name"])
        rec["nanoda_text"] = text[-500:]
        rec["seconds"] = round(time.time() - start, 1)
        with results.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(item["name"].ljust(40), item["outcome"].ljust(7), rec["official"].ljust(11), rec["nanoda"].ljust(9), rec.get("leanchecker_fresh", "-").ljust(9), rec["seconds"], flush=True)


main()
