p = "src/cport_r2.c"
s = open(p).read()
old = '''            const char *vd = verdict480(&rr, Ub, bstr, &closes);
            ncl +='''
new = '''            const char *vd = verdict480(&rr, Ub, bstr, &closes);
            if (rr.budget) printf("BUDGET detail: mitm space=%.4g left=%.4g right=%.4g (limits: space 6e16, right 5e9, case budget %ld) words=%d\\n", g_mitm_space, g_mitm_left, g_mitm_right, maxcases, rr.nwords);
            ncl +='''
assert s.count(old) == 1
open(p, "w").write(s.replace(old, new))
