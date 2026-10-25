import hashlib
new = {}
for ln in open("data/utable_u2_k34.txt"):
    k, a, v = ln.split()
    new[(int(k), int(a))] = int(v)
old = {}
for ln in open("../cport-shadow/data/utable_u2_k29.txt"):
    k, a, v = ln.split()
    old[(int(k), int(a))] = int(v)
bad = [key for key in old if new.get(key) != old[key]]
sub = [ln for ln in open("data/utable_u2_k34.txt") if int(ln.split()[0]) <= 29 and int(ln.split()[1]) <= 24]
subtxt = "".join(sub).encode()
oldtxt = open("../cport-shadow/data/utable_u2_k29.txt", "rb").read()
print("old rows", len(old), "new rows", len(new), "mismatches", len(bad))
print("byte equal", subtxt == oldtxt, hashlib.md5(subtxt).hexdigest(), hashlib.md5(oldtxt).hexdigest())
import math
for k in (30, 31, 32, 33, 34):
    print(k, [round(math.log10(new[(k, a)]), 2) for a in (0, 1, 4, 24, 60)])
