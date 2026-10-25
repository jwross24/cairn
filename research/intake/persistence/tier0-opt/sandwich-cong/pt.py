import json, math
SH = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2shadow/data/"
for i in ("s000", "t121", "t348"):
    w = json.loads(open("runs/words_%s.jsonl" % i).readline())
    bs = [(int(x), int(y)) for x, y in w["basis"]]
    T = []
    for line in open(SH + "levelprimes480.txt"):
        if line[0] in "#\n" or line.split()[0] not in ("480",): continue
        p = int(line.split()[1])
        ok = all(pow(3, b % (p - 1), p) * pow(7, c % (p - 1), p) % p == 1 for b, c in bs)
        if ok: T.append(p)
    pt = math.prod(T)
    print(i, T, "PT=%.3g" % pt)
