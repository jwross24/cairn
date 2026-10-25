import sys, json, hashlib

def load_prod(path, q):
    out = {}
    for l in open(path):
        f = l.split()
        if not f: continue
        a, nu = int(f[0]), int(f[1]); eps = tuple(int(x) for x in f[2:2 + q])
        v0 = (int(f[2 + q]), int(f[3 + q])); u1 = (int(f[4 + q]), int(f[5 + q])); u2 = (int(f[6 + q]), int(f[7 + q]))
        out[(a, nu, eps)] = (v0, u1, u2)
    return out

def load_dual(paths, q):
    out = {}
    for p in paths:
        for l in open(p):
            f = l.split()
            if not f: continue
            a, nu = int(f[0]), int(f[1]); eps = tuple(int(x) for x in f[2:2 + q]); b, c = int(f[2 + q]), int(f[3 + q])
            key = (a, nu, eps)
            if key in out: out.setdefault('__dup__', []).append(key)
            out[key] = (b, c)
    return out

def in_lattice(d, u1, u2):
    det = u1[0] * u2[1] - u1[1] * u2[0]
    x = d[0] * u2[1] - d[1] * u2[0]; y = u1[0] * d[1] - u1[1] * d[0]
    return x % det == 0 and y % det == 0

if __name__ == '__main__':
    prod = load_prod(sys.argv[1], int(sys.argv[2])); q = int(sys.argv[2])
    dual = load_dual(sys.argv[3:], q)
    dup = dual.pop('__dup__', [])
    pk, dk = set(prod), set(dual)
    coset_bad = [k for k in pk & dk if not in_lattice((dual[k][0] - prod[k][0][0], dual[k][1] - prod[k][0][1]), prod[k][1], prod[k][2])]
    def h(keys):
        return hashlib.sha256(''.join(f"{a} {nu} {' '.join(map(str, e))}\n" for a, nu, e in sorted(keys)).encode()).hexdigest()
    print(json.dumps(dict(prod=len(pk), dual=len(dk), only_prod=len(pk - dk), only_dual=len(dk - pk), dups=len(dup), coset_mismatch=len(coset_bad),
                          identical=(pk == dk and not coset_bad and not dup), sha_prod=h(pk)[:16], sha_dual=h(dk)[:16])))
