s = open("lvl24_blind.c").read()
a = "static void flush_batch(void)\n{\n    if (!batch_n)\n        return;\n"
assert s.count(a) == 1
s = s.replace(a, "static long INSTR_hist[5];\nstatic void flush_batch(void)\n{\n    if (!batch_n)\n        return;\n    INSTR_hist[batch_n]++;\n")
b = "        if (selected < 0)\n            die(\"requested join key set is unavailable\");\n    }\n}"
assert s.count(b) == 1
s = s.replace(b, b[:-1] + "    if (getenv(\"INSTR_KEY\")) { char nm[64]; key_name(&keyset[selected], nm); fprintf(stderr, \"INSTR key %s\\n\", nm); }\n}")
c = "    fclose(f);\n    fprintf(stderr,\n        \"parents %d children"
assert s.count(c) == 1
s = s.replace(c, "    fclose(f);\n    fprintf(stderr, \"INSTR batch1 %ld batch2 %ld batch3 %ld batch4 %ld\\n\", INSTR_hist[1], INSTR_hist[2], INSTR_hist[3], INSTR_hist[4]);\n    fprintf(stderr,\n        \"parents %d children")
open("lvl24_blind_instr.c", "w").write(s)
