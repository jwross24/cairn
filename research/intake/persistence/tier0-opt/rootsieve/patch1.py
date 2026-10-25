import re
p = "rs.c"
t = open(p).read()
t = t.replace("""  int dumpit = dump_prob > 0 && (rnd() >> 11) * (1.0 / 9007199254740992.0) < dump_prob;
  char buf[4096]; int bl = 0;
  if (dumpit) { bl += sprintf(buf + bl, "S %d %d %d", rk, nu, q); for (int j = 0; j < q; j++) bl += sprintf(buf + bl, " %d:%d", digits[j], eps[j]); }""",
"""  int dumpit = dump_prob > 0 && (rnd() >> 11) * (1.0 / 9007199254740992.0) < dump_prob;
  char buf[4096]; int bl = 0;
  bl += sprintf(buf + bl, "S %d %d %d", rk, nu, q); for (int j = 0; j < q; j++) bl += sprintf(buf + bl, " %d:%d", digits[j], eps[j]);""")
t = t.replace("""    if (dumpit) bl += sprintf(buf + bl, " | %lld %d %d %lld %lld", a0, keep, open, b, c);""",
"""    bl += sprintf(buf + bl, " | %lld %d %d %lld %lld", a0, keep, open, b, c);""")
t = t.replace("""  if (dumpit) { buf[bl++] = '\\n'; fwrite(buf, 1, bl, dumpf); }""",
"""  if (dumpit || any_open_keep) { buf[bl++] = '\\n'; fwrite(buf, 1, bl, dumpf); }""")
open(p, "w").write(t)
