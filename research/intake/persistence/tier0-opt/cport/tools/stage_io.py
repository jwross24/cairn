import json


def entries(path):
    for line in open(path):
        r = json.loads(line)
        if 'eqs' not in r:
            continue
        for eq in r['eqs']:
            if isinstance(eq, dict):
                M, ex = eq['M'], eq.get('exceptional', [])
                for e in ex:
                    if len(e) == 3:
                        a, y, sol = e
                        yield r['s'], tuple(M), a, None, None, y, sol
                    else:
                        yield r['s'], tuple(M), e[1], e[2], e[3], e[4][0], e[4][1]
        for e in r.get('exceptional', []):
            M, a, nu, eps, (y, sol) = e
            yield r['s'], tuple(M), a, nu, eps, y, sol


def full_key(s, M, a, nu, eps, y):
    nus = '-' if nu is None else str(nu)
    epss = '-' if eps is None else (','.join(map(str, eps)) or ',')
    return f"{s} {''.join(map(str, M))} {a} {y} {nus} {epss}"


def records(paths):
    for p in paths:
        for (s, M, a, nu, eps, y, sol) in entries(p):
            yield (s, M, a, nu, eps, y), full_key(s, M, a, nu, eps, y)


def snapshot(src, dst):
    data = open(src, 'rb').read()
    cut = data.rfind(b'\n') + 1
    open(dst, 'wb').write(data[:cut])
    return cut
