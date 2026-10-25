import sys, json
from math import isqrt

pts, out_close, out_refuse = sys.argv[1:4]
nn = min(int(json.loads(l)['nn']) for l in open(pts))
l = 4771212547


def closes(U):
    return nn * l * l > 2 * U * U * 10 ** 20


Ub = isqrt((nn * l * l - 1) // (2 * 10 ** 20))
while not closes(Ub):
    Ub -= 1
while closes(Ub + 1):
    Ub += 1
assert closes(Ub) and not closes(Ub + 1)
for path, U in ((out_close, Ub), (out_refuse, Ub + 1)):
    with open(path, 'x') as f:
        f.write(f"31 0 {U}\n")
print('boundary U =', Ub, 'digits', len(str(Ub)), '; closes at U:', closes(Ub), '; closes at U+1:', closes(Ub + 1))
