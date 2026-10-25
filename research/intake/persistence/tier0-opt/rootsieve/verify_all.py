import subprocess
out = open("soundness.out", "w")
for name, meta, chk in (("plants", "plants_meta.txt", "plants_chk_%d.txt"), ("open@96 items", "openpat_meta.txt", "openpat_chk_%d.txt")):
    for m, label in ((0, "production predicate"), (1, "mutant 1: 3-adic branch inverted"), (2, "mutant 2: 7-adic branch inverted"), (3, "mutant 3: b shifted by one")):
        r = subprocess.run(["uv", "run", "--no-project", "python", "-I", "verify_check.py", meta, chk % m], capture_output=True, text=True)
        out.write("== %s, %s\n%s\n" % (name, label, "\n".join(r.stdout.splitlines()[:2])))
out.close()
