import hashlib, sys
def sha(b): return hashlib.sha256(b).hexdigest()
def prefix_ok(new_bytes, old_bytes, dmax=4000):
    lines = new_bytes.split(b"\n")
    keep = [l for l in lines if l and int(l.split()[1]) <= dmax]
    pre = b"\n".join(keep) + b"\n"
    return len(pre) == len(old_bytes) and sha(pre) == sha(old_bytes), len(pre), sha(pre)
if __name__ == "__main__":
    new = open(sys.argv[1], "rb").read()
    old = open(sys.argv[2], "rb").read()
    ok, n, h = prefix_ok(new, old)
    print("old len", len(old), sha(old))
    print("prefix len", n, h, "MATCH" if ok else "MISMATCH")
    ol = old.split(b"\n")[:-1]
    dropped = b"\n".join(ol[:4000] + ol[4001:]) + b"\n"
    ok1, n1, _ = prefix_ok(new, dropped)
    print("planted negative, one element dropped from reference:", "ACCEPTED (check is broken)" if ok1 else "REFUSED")
    parts = ol[5000].split()
    parts[4] = str(int(parts[4]) + 1).encode()
    altered = b"\n".join(ol[:5000] + [b" ".join(parts)] + ol[5001:]) + b"\n"
    ok2, n2, _ = prefix_ok(new, altered)
    print("planted negative, one element altered in reference:", "ACCEPTED (check is broken)" if ok2 else "REFUSED")
    nl = new.split(b"\n")[:-1]
    keep = [l for l in nl if int(l.split()[1]) <= 4000]
    drop = b"\n".join(keep[:777] + keep[778:]) + b"\n"
    ok3, _, _ = prefix_ok(drop, old)
    print("planted negative, one element dropped from the new corpus:", "ACCEPTED (check is broken)" if ok3 else "REFUSED")
    sys.exit(0 if ok and not (ok1 or ok2 or ok3) else 1)
