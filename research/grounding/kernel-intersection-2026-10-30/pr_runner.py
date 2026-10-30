import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys

WORK = pathlib.Path(sys.argv[1])
CONTAINER = "p76j-probe"
ENV = "export PATH=/home/cairn/lean/bin:/home/cairn/.elan/bin:/usr/local/bin:/usr/bin:/bin; "
LEAN4EXPORT = "/home/cairn/comparator/.lake/packages/lean4export/.lake/build/bin/lean4export"
PROBE = "/work/driver/.lake/build/bin/probe"
GUARD = re.compile(r"/--\s*(?:\n)?error: kernel error\s*(?:\n)?-/\n#guard_msgs in\n")
CASES = [
    ("pr14807", "kernel_is_prop_ensure_sort.lean", "kernel_soundness_target"),
    ("pr14806_2", "kernel_is_def_eq_equiv_manager_2.lean", "inconsistent"),
]


def sh(script, timeout=420):
    r = subprocess.run(["docker", "exec", CONTAINER, "sh", "-c", ENV + script], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def run(name, source, target):
    text = (WORK / "pr" / source).read_text()
    patched, count = GUARD.subn("", text)
    project = WORK / "lean" / name
    project.mkdir(parents=True, exist_ok=True)
    (project / "Test.lean").write_text(patched)
    (project / "lean-toolchain").write_text("leanprover/lean4:v4.34.0-rc1\n")
    (project / "lakefile.toml").write_text('name = "test"\n\n[[lean_lib]]\nname = "Test"\n')
    guest = f"/work/lean/{name}"
    rc, build = sh(f"cd {guest} && timeout 300 lake build Test")
    rec = {"name": name, "guards_removed": count, "build_rc": rc, "build_tail": build[-900:]}
    if rc == 0:
        export = f"/work/out/{name}.ndjson"
        rc2, text2 = sh(f"cd {guest} && timeout 300 lake env {LEAN4EXPORT} Test -- {shlex.quote(target)} > {export}")
        rec["export_rc"] = rc2
        rec["export_text"] = text2[-300:]
        host = WORK / "out" / f"{name}.ndjson"
        rec["export_bytes"] = host.stat().st_size
        rec["export_sha256"] = hashlib.sha256(host.read_bytes()).hexdigest()
        rc3, t3 = sh(f"timeout 300 {PROBE} {export}")
        rec["official_rc"], rec["official_text"] = rc3, t3[-500:]
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
        rc5, t5 = sh(f"cd {guest} && timeout 300 lake env /home/cairn/lean/bin/leanchecker --fresh -v Test")
        rec["leanchecker_rc"], rec["leanchecker_text"] = rc5, t5[-500:]
    return rec


with (WORK / "out" / "pr_results.jsonl").open("a") as f:
    for case in CASES:
        rec = run(*case)
        f.write(json.dumps(rec) + "\n")
        f.flush()
        print(json.dumps(rec, indent=1, ensure_ascii=False)[:2400], flush=True)
