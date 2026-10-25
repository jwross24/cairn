import sys, os, json, math, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1tier import *

FROZEN = os.environ.get('N1_FROZEN', '/private/tmp/n1work')


def n_bases(surv1_remaining, E):
    """unlabeled depth-E bases: sum over depth-1 survivors of the number of fillings of blocks 1..E-1."""
    return sum(count_blocks(rem, E - 1) for rem in surv1_remaining)


def n_enum(types, D, p1):
    """unlabeled depth-D sub-cosets reached by pure enumeration, with depth-1 survival probability p1."""
    return count_blocks(types, 1) * p1 * (count_blocks(types, D) / count_blocks(types, 1))


def tierc_table():
    types = tierc_types()
    s1 = json.load(open(os.path.join(FROZEN, 'tierc_surv1.json')))
    rems = [tinsert(types, [tuple(x) for x in ch]) for ch, *_ in s1]
    rows = []
    for E in range(1, 7):
        rows.append((E, n_bases(rems, E)))
    return types, rems, rows


def scaled_types(q):
    """Tier-C class skeleton with the 2-multiplicities of classes 5 and 6 (and 3s in 8, 9) grown to reach q digits."""
    t = tierc_types()
    i = 0
    order = [(2, 5), (2, 6), (3, 9), (3, 8), (2, 7), (2, 8), (2, 9), (2, 4), (2, 3), (2, 2)]
    while sum(t.values()) < q:
        t[order[i % len(order)]] += 1
        i += 1
    return t


if __name__ == '__main__':
    types, rems, rows = tierc_table()
    print('Tier-C q =', sum(types.values()), 'classes', len({e for _, e in types}), 'types', len(types))
    print('depth-1 survivors', len(rems), 'block fillings (unlabeled)', count_blocks(types, 1))
    for E, n in rows:
        print('E', E, 'depth-E bases', n, f'log10 {math.log10(n):.2f}' if n else '')
    for D in range(1, 11):
        print('pure enumeration D', D, 'sub-cosets', f'{n_bases(rems, D):.3e}')
    for q in (31, 36, 40, 44):
        tt = scaled_types(q)
        print('q', q, 'fillings/block', count_blocks(tt, 1), 'N_E (p1 as Tier C):',
              {E: f'{len(rems) * count_blocks(tt, E - 1):.2e}' if E > 1 else len(rems) for E in (2, 3, 4, 5)},
              'pure D=6,8:', {D: f'{len(rems) * count_blocks(tt, D - 1):.2e}' for D in (6, 8)})
