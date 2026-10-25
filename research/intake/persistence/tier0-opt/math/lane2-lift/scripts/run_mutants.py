import subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
specs = [("L0","M1"),("L0","M2"),("A","M1"),("A","M2"),("A","AMUT"),("C","M1"),("C","M2"),("C","CMUT"),("E","M1"),("E","M2"),("BEST","M1"),("BEST","M2"),("BEST","CMUT"),("BEST","AMUT")]
for n, m in specs:
    subprocess.run([sys.executable, "-I", os.path.join(here, "mutants.py"), n, m], check=False)
