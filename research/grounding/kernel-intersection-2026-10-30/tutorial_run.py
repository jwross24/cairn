import collections
import json
import pathlib
import subprocess
import sys

P = pathlib.Path(sys.argv[1])
OUT = P / "out"
TUT = OUT / "tutorial"
PROBES = {
    "v4.34.0-rc1": "/work/driver/.lake/build/bin/probe",
    "v4.34.1": "/tmp/p76j/drv-4.34.1/.lake/build/bin/probe",
    "v4.35.0": "/tmp/p76j/drv-4.35.0/.lake/build/bin/probe",
}
AXIOMS = ["propext", "Classical.choice", "Quot.sound"]
ENV = "export PATH=/home/cairn/lean/bin:/home/cairn/.elan/bin:/usr/local/bin:/usr/bin:/bin; "


def docker(*argv, timeout=180):
    return subprocess.run(["docker", "exec", "p76j-probe", *argv], capture_output=True, text=True, timeout=timeout)


def official(probe, guest):
    r = docker("timeout", "120", probe, guest)
    return {0: "ACCEPT", 1: "REJECT", 2: "PARSE-FAIL", 124: "TIMEOUT"}.get(r.returncode, f"RC-{r.returncode}")


def config(path):
    return json.dumps(
        {
            "use_stdin": False,
            "export_file_path": str(path),
            "permitted_axioms": AXIOMS,
            "unpermitted_axiom_hard_error": True,
            "nat_extension": True,
            "string_extension": True,
        }
    )


def nanoda_label(rc, text):
    if rc == 0:
        return "ACCEPT"
    if rc == 124:
        return "TIMEOUT"
    if "Declined" in text:
        return "DECLINED"
    if text.startswith("Error:") or "\nError:" in text:
        return "CONFIG"
    return "KERNEL-REFUSE"


def nanoda_image(guest, stem):
    (OUT / f"tut-{stem}.nanoda.json").write_text(config(guest))
    r = docker("timeout", "120", "/usr/local/bin/nanoda_bin", f"/work/out/tut-{stem}.nanoda.json")
    return nanoda_label(r.returncode, r.stdout + r.stderr), (r.stdout + r.stderr)[-200:]


def nanoda_head(host, stem):
    cfg = OUT / f"tut-{stem}.host.json"
    cfg.write_text(config(host))
    r = subprocess.run([str(P / "nanoda/head/target/release/nanoda_bin"), str(cfg)], capture_output=True, text=True, timeout=180)
    return nanoda_label(r.returncode, r.stdout + r.stderr)


rows = []
for outcome, sub in (("reject", "bad"), ("accept", "good")):
    for path in sorted((TUT / sub).glob("*.ndjson")):
        guest = f"/work/out/tutorial/{sub}/{path.name}"
        row = {"name": path.stem, "outcome": outcome}
        for label, probe in PROBES.items():
            row[label] = official(probe, guest)
        row["nanoda_pin"], row["nanoda_text"] = nanoda_image(guest, path.stem)
        row["nanoda_head"] = nanoda_head(path, path.stem)
        rows.append(row)

(OUT / "tutorial_results.json").write_text(json.dumps(rows, indent=1))
for outcome in ("reject", "accept"):
    part = [r for r in rows if r["outcome"] == outcome]
    print(outcome, len(part))
    for key in (*PROBES, "nanoda_pin", "nanoda_head"):
        print("  ", key.ljust(13), dict(collections.Counter(r[key] for r in part)))
bad = [r for r in rows if r["outcome"] == "reject"]
print("BOTH-PINNED-ACCEPT", [r["name"] for r in bad if r["v4.34.0-rc1"] == "ACCEPT" and r["nanoda_pin"] == "ACCEPT"])
for key in (*PROBES, "nanoda_pin", "nanoda_head"):
    print("reject-accepted", key, [r["name"] for r in bad if r[key] == "ACCEPT"])
for key in (*PROBES, "nanoda_pin", "nanoda_head"):
    print("accept-missed", key, [(r["name"], r[key]) for r in rows if r["outcome"] == "accept" and r[key] != "ACCEPT"][:10])
