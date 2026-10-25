import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
import export_cfg
M = tuple(int(x) for x in sys.argv[1].split(","))
cfg = export_cfg.export(M, sys.argv[2])
print("A=", cfg["A"], "digits", cfg["digits"])
