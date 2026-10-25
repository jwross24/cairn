p = "run_surv.py"
s = open(p).read()
s = s.replace('BIN = P + "tierc-r2shadow/cport_r2c"', 'BIN = os.environ.get("TB_BIN", P + "tierc-r2shadow/cport_r2c")\nEXTRA = os.environ.get("TB_FLAGS", "").split()')
s = s.replace('+ (RAISED if raised else [])', '+ EXTRA + (RAISED if raised else [])')
open(p, "w").write(s)
