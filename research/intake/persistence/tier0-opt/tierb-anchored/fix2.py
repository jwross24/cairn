p = "enum_surv.c"
s = open(p).read()
s = s.replace("static unsigned long long rng_s = 88172645463325252ULL;\nstatic u64 rnd(void) { rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17; return rng_s; }\n", "")
s = s.replace("static signed char stk[NPOS][7];", "static unsigned long long rng_s = 88172645463325252ULL;\nstatic u64 rnd(void) { rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17; return rng_s; }\nstatic double emit_p = 1.0;\nstatic signed char stk[NPOS][7];")
s = s.replace("        if (mode_emit) {\n            int ndd[400]", "        if (mode_emit && (emit_p >= 1.0 || (double)(rnd() >> 11) * (1.0 / 9007199254740992.0) < emit_p)) {\n            int ndd[400]")
s = s.replace("    if (argc >= 6) rng_s ^= (u64)atoll(argv[5]) * 0x9E3779B97F4A7C15ULL;", "    if (argc >= 6) rng_s ^= (u64)atoll(argv[5]) * 0x9E3779B97F4A7C15ULL;\n    if (argc >= 7) emit_p = atof(argv[6]);")
open(p, "w").write(s)
