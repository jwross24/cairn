"""capture.py <srcdir> <out.pkl> <s> <M or ALL> -- record every classify() input of a production run"""
import sys, os, pickle
srcdir, outp, s, eq = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.chdir(srcdir); sys.path.insert(0, srcdir)
import tier0v2, run_c
rec = []
_c = tier0v2.classify
def cl(co, a, D, nu, eps, L, M, kcap):
    rec.append((a, nu, tuple(eps), tuple(co.v0), tuple(co.u1), tuple(co.u2), tuple(D), L, kcap))
    return _c(co, a, D, nu, eps, L, M, kcap)
tier0v2.classify = cl
eqs = [tuple(sorted(M)) for M in tier0v2.multisets(s)] if eq == 'ALL' else [tuple(int(x) for x in eq.split(','))]
for M in eqs:
    run_c.run(s, M, [], ncores=2)
pickle.dump(rec, open(outp, 'wb'))
print(len(rec), 'records')
