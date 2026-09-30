import sys

from cairn.skills import order_bsgs_gmpy2, toy_curve

REAL_GROUP_ORDER = order_bsgs_gmpy2.group_order
CALLS = []


def shifted_order(p, a, b, points):
    CALLS.append((p, a, b, points))
    if len(CALLS) != 1:
        raise AssertionError("independent order oracle retried")
    return REAL_GROUP_ORDER(p, a, b, points) + 1


def main():
    setattr(order_bsgs_gmpy2, REAL_GROUP_ORDER.__name__, shifted_order)
    code = toy_curve.main()
    if len(CALLS) != 1:
        raise AssertionError("independent order oracle did not execute exactly once")
    return code


if __name__ == "__main__":
    sys.exit(main())
