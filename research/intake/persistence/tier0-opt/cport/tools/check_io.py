import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PY = os.environ['CPORT_PYREF_DIR']
os.chdir(PY)
sys.path.insert(0, PY)
import classify_open as C
from stage_io import entries

bad = 0
n = 0
for f in sys.argv[1:]:
    a = list(C.entries(f))
    b = list(entries(f))
    n += len(a)
    if a != b:
        bad += 1
print(f"entries(): {n} records over {len(sys.argv) - 1} files, files differing from classify_open.entries: {bad}")
sys.exit(1 if bad else 0)
