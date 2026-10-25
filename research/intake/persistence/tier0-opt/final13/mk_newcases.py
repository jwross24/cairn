import os
SN = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/kt-audit-l12/shadow-new/inputs/'
V13 = {'331776', '11239424', '3779136', '2939328', '69441624', '3281116734', '1161216', '7112448', '13226976', '46294416', '1741824', '1492992', '9483264'}
os.makedirs('newcases')
lines = []
for f in ('new1_cases.txt', 'new3_cases.txt'):
    lines += [l.rstrip('\n') for l in open(SN + f) if l.strip() and l.split()[0] in V13]
with open('newcases/cases.txt', 'x') as fc, open('newcases/only.txt', 'x') as fo:
    for l in lines:
        fc.write(l + '\n')
        fo.write(' '.join(l.split()[:4]) + '\n')
print(len(lines))
