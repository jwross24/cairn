import hashlib
src = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/sandwich-cong/src/cport_cong.c"
dst = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/ptprobe/cport_cong_pt.c"
text = open(src).read()
print("src md5", hashlib.md5(text.encode()).hexdigest())
anchor = "    if (nT == 0) { rr->nonappl++;"
assert text.count(anchor) == 1
probe = '    fprintf(stderr, "PTLOG %llu %d\\n", (unsigned long long)PT, nT);\n'
open(dst, "w").write(text.replace(anchor, probe + anchor))
print("written")
