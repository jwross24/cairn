import json, sys, time, datetime
from fonga_v2 import exact_max_v2, Budget

VERTICES = [
    (2, 6, 3, 27, 1),
    (3, 23, 7, 1),
    (4, 29, 5, 1),
    (5, 39, 3, 2),
    (6, 34, 8, 0),
    (7, 24, 6, 6),
]
rows = [(6, 27, 1), (23, 7, 1), (29, 5, 1), (39, 3, 2), (34, 8, 0), (24, 6, 6)]
rows = [(6, 27, 1), (23, 7, 1), (29, 5, 1), (24, 6, 6), (34, 8, 0), (39, 3, 2)]
cap = int(float(sys.argv[1]))
only = int(sys.argv[2]) if len(sys.argv) > 2 else None
out = open("tierc.jsonl", "a")
for i, (a, b, c) in enumerate(rows):
    if only is not None and i != only:
        continue
    M = (2,) * a + (3,) * b + (7,) * c
    t = time.time()
    st = {}
    try:
        r = exact_max_v2(M, node_limit=cap, stats=st)
    except Budget:
        r = None
    out.write(json.dumps({"a": a, "b": b, "c": c, "k": len(M), "A": r, "nodes": st.get("nodes"), "secs": round(time.time() - t, 1), "when": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
    out.flush()
