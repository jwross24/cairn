import subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
env = dict(os.environ); env["MUTBIN"] = os.path.join(root, "src", "lane2_mut2")
for n in ("DH", "LA", "LA_A"):
    subprocess.run([sys.executable, "-I", os.path.join(here, "eval.py"), n], check=False)
for n, m in (("DH","M1"),("DH","M2"),("LA","M1"),("LA","M2"),("C","CMUT2"),("BEST","CMUT2")):
    subprocess.run([sys.executable, "-I", os.path.join(here, "mutants.py"), n, m], check=False, env=env)
