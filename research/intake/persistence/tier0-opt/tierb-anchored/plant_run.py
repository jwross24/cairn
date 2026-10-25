import subprocess, sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierb-anchored")
import ref_check as RC, os
os.chdir("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierb-anchored")
src, planted, A, B, Cc = sys.argv[1:6]
orig = [l.split() for l in open(src) if not l.startswith("T")][:6]
def verdicts(path):
    r = subprocess.run(["./enum_surv", A, B, Cc, "verdict"], stdin=open(path), capture_output=True, text=True).stdout.split("\n")
    return [int(l.split()[4]) for l in r if l.strip()]
with open("work/_orig_v.txt", "w") as f:
    for t in orig:
        f.write(" ".join(t[:3] + t[5:]) + "\n")
vo = verdicts("work/_orig_v.txt")
vp = verdicts(planted)
print("original survivors: C verdicts", vo)
for i, l in enumerate(open(planted)):
    t = l.split()
    y = int(t[0]); De = [tuple(map(int, x.split(":"))) for x in t[3:]]
    ex, red = RC.exact_verdict(y, De)
    ox, _ = RC.exact_verdict(int(orig[i][0]), [tuple(map(int, x.split(":"))) for x in orig[i][5:]])
    print(i, "original exact", ox, "C", vo[i], "| planted exact", ex, "C", vp[i])
