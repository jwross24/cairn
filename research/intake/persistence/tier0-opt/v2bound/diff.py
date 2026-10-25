import json, sys, time, datetime
from fonga_v2 import exact_max_v2, Budget, Reached
from oldbound import old_capped, StateCap
from plants import recorded, zf_units, digits_of, mpz

phase = sys.argv[1]
deadline_h, deadline_m = 1, 40
out = open(f"diff_{phase}.jsonl", "w")


def late():
    n = datetime.datetime.now()
    return (n.hour, n.minute) >= (deadline_h, deadline_m) and n.hour < 5


def emit(rec):
    out.write(json.dumps(rec) + "\n")
    out.flush()


def v2int(y):
    y = int(y)
    return (y & -y).bit_length() - 1


def plant_list():
    items = []
    ms, kids = recorded()
    for y in kids:
        M, zero = digits_of(mpz(y))
        if not zero:
            items.append(("child", y, M, v2int(y)))
    for a, b, c in zf_units():
        y = mpz(2) ** a * mpz(3) ** b * mpz(7) ** c
        M, zero = digits_of(y)
        items.append(("zf", f"{a},{b},{c}", M, a))
    items.sort(key=lambda r: len(r[2]))
    return items


if phase == "recorded":
    ms, _ = recorded()
    for M in sorted(ms, key=lambda m: (len(m), m)):
        if late():
            emit({"stop": "deadline"}); break
        rec = {"M": M, "k": len(M)}
        try:
            rec["old"] = old_capped(M, state_cap=int(sys.argv[2]))
        except StateCap:
            rec["old"] = None
        st = {}
        t = time.time()
        try:
            rec["new"] = exact_max_v2(M, node_limit=int(sys.argv[3]), stats=st)
        except Budget:
            rec["new"] = None
        rec["secs"] = round(time.time() - t, 3)
        emit(rec)

elif phase == "plants":
    for kind, key, M, a in plant_list():
        if late():
            emit({"stop": "deadline"}); break
        rec = {"kind": kind, "key": key, "k": len(M), "a": a}
        try:
            r = exact_max_v2(M, node_limit=int(sys.argv[2]), target=a)
            rec["status"] = "ok" if r >= a else "violation"
        except Reached:
            rec["status"] = "ok"
        except Budget:
            rec["status"] = "capped"
        emit(rec)

elif phase == "mutants":
    kmax = int(sys.argv[2])
    muts = {"slack-1": dict(slack=-1), "leading_lo2": dict(leading_lo=2), "slack+1": dict(slack=1), "leading_lo0": dict(leading_lo=0)}
    for kind, key, M, a in plant_list():
        if len(M) > kmax:
            break
        if late():
            emit({"stop": "deadline"}); break
        base = exact_max_v2(M)
        rec = {"kind": kind, "key": key, "k": len(M), "a": a, "base": base}
        for name, kw in muts.items():
            rec[name] = exact_max_v2(M, **kw)
        emit(rec)
