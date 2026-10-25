import subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
t = os.path.join(here, "timing.py")
eqs = "9437184_222222222228889,3211264_222222222222222277,393216_222222222222222223"
subprocess.run([sys.executable, "-I", t, "J24,L0,E0,A,A_E0,C,C_E0,E,BEST,DH,LA", "3", "0", eqs])
subprocess.run([sys.executable, "-I", t, "L0,B0,B1,B2,B3,B4", "1", "0", "393216_22222222222222226,3211264_222222222222222277"])
