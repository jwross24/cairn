import hashlib
import json
import pathlib
import shlex
import subprocess
import sys

WORK = pathlib.Path(sys.argv[1])
CONTAINER = "p76j-probe"
ENV = "export PATH=/home/cairn/lean/bin:/home/cairn/.elan/bin:/usr/local/bin:/usr/bin:/bin; "
LEAN4EXPORT = "/home/cairn/comparator/.lake/packages/lean4export/.lake/build/bin/lean4export"
PROBE = "/work/driver/.lake/build/bin/probe"
CASES = [
    ("bugs__nested-unused-param", "reject", "Bugs.NestedUnusedParam", "boom"),
    ("bugs__proj-of-stuck-prop", "reject", "Bugs.ProjOfStuckProp", "inconsistent"),
    ("corner-cases__nested-nonuniform-param", "either", "CornerCases.NestedNonuniformParam", "E"),
]


def sh(script, timeout=720):
    r = subprocess.run(["docker", "exec", CONTAINER, "sh", "-c", ENV + script], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


rows = []
for name, outcome, module, target in CASES:
    rec = {"name": name, "group": name.split("__")[0], "outcome": outcome, "route": "dir"}
    rc, build = sh(f"cd /work/tut && timeout 600 lake build {module}")
    rec["build_rc"], rec["build_log_tail"] = rc, build[-700:]
    if rc != 0:
        rec["official"] = rec["nanoda"] = "BUILD-FAIL"
    else:
        export = f"/work/out/{name}.ndjson"
        rc2, text2 = sh(f"cd /work/tut && timeout 300 lake env {LEAN4EXPORT} {module} -- {shlex.quote(target)} > {export}")
        rec["export_rc"], rec["export_text"] = rc2, text2[-300:]
        host = WORK / "out" / f"{name}.ndjson"
        rec["export_bytes"] = host.stat().st_size
        rec["export_sha256"] = hashlib.sha256(host.read_bytes()).hexdigest()
        rc3, t3 = sh(f"timeout 300 {PROBE} {export}")
        rec["official_rc"], rec["official_text"] = rc3, t3[-500:]
        rec["official"] = {0: "ACCEPT", 1: "REJECT", 2: "PARSE-FAIL"}.get(rc3, f"RC-{rc3}")
        config = {
            "use_stdin": False,
            "export_file_path": export,
            "permitted_axioms": ["propext", "Classical.choice", "Quot.sound"],
            "unpermitted_axiom_hard_error": True,
            "nat_extension": True,
            "string_extension": True,
        }
        (WORK / "out" / f"{name}.nanoda.json").write_text(json.dumps(config, separators=(",", ":")))
        rc4, t4 = sh(f"timeout 300 /usr/local/bin/nanoda_bin /work/out/{name}.nanoda.json")
        rec["nanoda_rc"], rec["nanoda_text"] = rc4, t4[-500:]
        rec["nanoda"] = "ACCEPT" if rc4 == 0 else ("TIMEOUT" if rc4 == 124 else "NONZERO")
        rc5, t5 = sh(f"cd /work/tut && timeout 300 lake env /home/cairn/lean/bin/leanchecker --fresh -v {module}")
        rec["leanchecker_rc"], rec["leanchecker_text"] = rc5, t5[-400:]
    rows.append(rec)
    print(name.ljust(42), outcome.ljust(7), rec["official"].ljust(11), rec["nanoda"].ljust(9), rec.get("leanchecker_rc", "-"), flush=True)
    print("   official:", rec.get("official_text", "")[:220].replace("\n", " "), flush=True)
    print("   nanoda:", rec.get("nanoda_text", "")[:200].replace("\n", " "), flush=True)
    if rec["official"] == "BUILD-FAIL":
        print("   build:", rec["build_log_tail"][-500:], flush=True)

with (WORK / "out" / "dir_results.jsonl").open("a") as f:
    for rec in rows:
        f.write(json.dumps(rec) + "\n")
