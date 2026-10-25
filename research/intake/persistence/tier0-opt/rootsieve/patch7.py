t = open("lvl12_r2.c").read()
t = t.replace("static int fastp; static ull *ENT[MAXP];", "static int pos;\nstatic int fastp; static ull *ENT[MAXP];", 1)
open("lvl12_r2.c", "w").write(t)
