import sys
def parse(path):
    t = open(path).read().split()
    it = iter(t)
    nx = lambda: next(it)
    Lold, Lnew, A, q = int(nx()), int(nx()), int(nx()), int(nx())
    digits = [int(nx()) for _ in range(q)]
    np_ = int(nx())
    primes = []
    for _ in range(np_):
        p, L2, L3, L7, G, nf = [int(nx()) for _ in range(6)]
        fac = [(int(nx()), int(nx())) for _ in range(nf)]
        pow10 = [int(nx()) for _ in range(Lnew)]
        R = [int(nx()) for _ in range(Lnew)]
        has = int(nx())
        if has:
            for _ in range(p):
                nx()
        primes.append(dict(p=p, L2=L2, L3=L3, L7=L7, G=G, fac=fac, pow10=pow10, R=R))
    nc = int(nx())
    comps = []
    for _ in range(nc):
        cn = int(nx())
        cidx = [int(nx()) for _ in range(cn)]
        cmod = [int(nx()) for _ in range(cn)]
        ccrt = int(nx())
        hs = int(nx())
        ent = []
        for _ in range(hs):
            key = tuple(int(nx()) for _ in range(cn))
            rep = (int(nx()), int(nx()))
            ent.append((key, rep))
        comps.append(dict(cidx=cidx, cmod=cmod, ccrt=ccrt, hs=hs, ent=ent))
    N = int(nx())
    nlin = int(nx())
    lins = []
    for _ in range(nlin):
        lidx, lmod, lg1, lg2 = int(nx()), int(nx()), int(nx()), int(nx())
        lcrt = int(nx())
        lins.append(dict(lidx=lidx, lmod=lmod, lg1=lg1, lg2=lg2, lcrt=lcrt))
    Uold = [[int(nx()), int(nx())], [int(nx()), int(nx())]]
    Unew = [[int(nx()), int(nx())], [int(nx()), int(nx())]]
    KT = [int(nx()) for _ in range(A + 1)]
    return dict(Lold=Lold, Lnew=Lnew, A=A, q=q, digits=digits, primes=primes, comps=comps, N=N, lins=lins, Uold=Uold, Unew=Unew, KT=KT)
