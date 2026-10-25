import hashlib, sys
h = []
for p in sys.argv[1:]:
    b = open(p, "rb").read()
    h.append(hashlib.sha256(b).hexdigest())
    print(p, len(b), h[-1])
print("equal", len(set(h)) == 1)
sys.exit(0 if len(set(h)) == 1 else 1)
