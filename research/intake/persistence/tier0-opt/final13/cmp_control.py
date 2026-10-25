import sys
ref = {l.split()[0]: l.rstrip('\n') for l in open(sys.argv[1]) if l.startswith('s=')}
new = {l.split()[0]: l.rstrip('\n') for l in open(sys.argv[2]) if l.startswith('s=')}
for v in sys.argv[3:]:
    k = 's=' + v
    a, b = ref.get(k), new.get(k)
    print(v, 'byte-equal' if a == b and a is not None else 'DIFFERENT')
    print(' ref', a)
    print(' new', b)
