import sys
src, dst, kind = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
anchor = "  int need_c0=(y7%7)!=0;\n"
assert s.count(anchor) == 1
ins = {'swap37': "  if(need_b0&&!need_c0){ need_b0=0; need_c0=1; }\n", 'drop3': "  if(!need_b0&&need_c0){ need_b0=1; need_c0=1; }\n"}[kind]
open(dst, 'w').write(s.replace(anchor, anchor + ins))
