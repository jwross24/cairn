p = "rs.c"
t = open(p).read()
t = t.replace('bl += sprintf(buf + bl, "S %d %d %d", rk, nu, q);', 'bl += sprintf(buf + bl, "%c %d %d %d", dumpit ? \'U\' : \'O\', rk, nu, q);')
open(p, "w").write(t)
