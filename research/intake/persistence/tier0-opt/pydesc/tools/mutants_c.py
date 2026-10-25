import subprocess, sys, os
src = open('/private/tmp/persist-pydesc/work/pydesc.c').read()
muts = {
 'm1_a_eq_t': ("if (a == t) return 1;", "if (a == t + 1) return 1;"),
 'm2_t_lt_K': ("if (t < K) return 0;", "if (t <= K) return 0;"),
 'm3_Kp_le_a': ("if (Kp <= a) {\n        if (mpz_sgn(w) != 0) return 0;", "if (Kp < a) {\n        if (mpz_sgn(w) != 0) return 0;"),
 'm4_x1tab': ("static const int x1tab[5] = {-1, 0, 3, 1, 2};\n    u64 m = P5U[k];", "static const int x1tab[5] = {-1, 0, 1, 3, 2};\n    u64 m = P5U[k];"),
 'm5_contains': ("return mpz_divisible_p(xn, l->det) && mpz_divisible_p(yn, l->det);", "return mpz_divisible_p(xn, l->det);"),
 'm6_depth': ("if (depth >= MAXDEPTH) return 1;", "if (depth >= MAXDEPTH - 1) return 1;"),
 'm8_dup': ("if (avail[j0].d == avail[j].d && avail[j0].e == avail[j].e) { dup = 1; break; }", "if (avail[j0].d == avail[j].d) { dup = 1; break; }"),
 'm11_k2eq1': ("if (Kp - a != 1) FAIL();", "if (Kp - a != 2) FAIL();"),
 'm12_K2guard': ("if (K2 != Kp) FAIL();", "if (K2 > Kp + 5) FAIL();"),
 'm13_len': ("if (len != K) FAIL();", "if (len > K) FAIL();"),
 'm10_open': ("else if (K >= 1 && do_descent) {", "else if (K >= 2 && do_descent) {"),
}
sel = sys.argv[1:] or list(muts)
for name in sel:
    old, new = muts[name]
    assert src.count(old) == 1, (name, src.count(old))
    p = f'/private/tmp/persist-pydesc/mut/{name}.c'
    open(p, 'w').write(src.replace(old, new))
    r = subprocess.run(['cc', '-O2', '-Wno-unused', '-dynamiclib', '-I/opt/homebrew/include', '-o', f'/private/tmp/persist-pydesc/mut/{name}.dylib', p, '/opt/homebrew/lib/libgmp.a'], capture_output=True, text=True)
    print(name, 'build rc', r.returncode, r.stderr[:200])
