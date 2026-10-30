import json
import pathlib
import subprocess
import sys

P = pathlib.Path(sys.argv[1])
ARENA = pathlib.Path(sys.argv[2])
OUT = P / "out"
PROBES = {
    "v4.34.0-rc1": "/work/driver/.lake/build/bin/probe",
    "v4.34.1": "/tmp/p76j/drv-4.34.1/.lake/build/bin/probe",
    "v4.35.0": "/tmp/p76j/drv-4.35.0/.lake/build/bin/probe",
}
LIMIT = 50_000_000


def rows():
    merged = {}
    for name in ("results.jsonl", "dir_results.jsonl", "pr_results.jsonl"):
        for line in (OUT / name).read_text().splitlines():
            r = json.loads(line)
            r.setdefault("outcome", "reject")
            merged[r["name"]] = r
    return merged


def guest(r):
    local = OUT / f"{r['name']}.ndjson"
    if local.exists():
        return f"/work/out/{r['name']}.ndjson", local.stat().st_size
    rel = r["name"].replace("__", "/") + ".ndjson"
    host = ARENA / rel
    if host.exists():
        return f"/arena/{rel}", host.stat().st_size
    return None, 0


def verdict(probe, path):
    try:
        r = subprocess.run(
            ["docker", "exec", "p76j-probe", "timeout", "120", probe, path], capture_output=True, text=True, timeout=180
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    text = r.stdout + r.stderr
    return {0: "ACCEPT", 1: "REJECT", 2: "PARSE-FAIL", 124: "TIMEOUT"}.get(r.returncode, f"RC-{r.returncode}"), text[:240]


table = []
for name, r in sorted(rows().items()):
    path, size = guest(r)
    if path is None or size > LIMIT:
        continue
    entry = {"name": name, "outcome": r["outcome"]}
    for label, probe in PROBES.items():
        entry[label], entry[label + "_text"] = verdict(probe, path)
    table.append(entry)

(OUT / "official_compare.json").write_text(json.dumps(table, indent=1))
labels = list(PROBES)
rej = [t for t in table if t["outcome"] == "reject"]
print("rows", len(table), "reject", len(rej))
for label in labels:
    print(label, "accepts reject-rows:", [t["name"] for t in rej if t[label] == "ACCEPT"])
    print(label, "non-verdicts:", [(t["name"], t[label]) for t in table if t[label] not in ("ACCEPT", "REJECT")])
    print(label, "accept-control misses:", [t["name"] for t in table if t["outcome"] == "accept" and t[label] != "ACCEPT"])
for t in table:
    if len({t[label] for label in labels}) > 1:
        print("DIFF", t["name"].ljust(44), t["outcome"].ljust(7), " ".join(t[label].ljust(8) for label in labels))
