import sys
src, dst = sys.argv[1], sys.argv[2]
with open(dst, 'x') as f:
    for l in open(src):
        t = l.split()
        if len(t) == 3 and not l.startswith('#'):
            f.write(f'{t[0]} {t[1]} {10 ** 400}\n')
        else:
            f.write(l)
