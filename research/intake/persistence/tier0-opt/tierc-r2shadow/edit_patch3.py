p = "src/cport_r2.c"
s = open(p).read()

def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

sub("static double g_mitm_space, g_mitm_left, g_mitm_right;", "static double g_mitm_space, g_mitm_left, g_mitm_right;\nstatic double g_cap_space = 6e16, g_cap_right = 5e9;")
sub("    if (tot > 6e16) return 1;", "    if (tot > g_cap_space) return 1;")
sub("    if ((double)NR > 5e9) return 1;", "    if ((double)NR > g_cap_right) return 1;")
sub('''        else if (!strcmp(argv[i], "--rep-file")) repf = argv[++i];''', '''        else if (!strcmp(argv[i], "--rep-file")) repf = argv[++i];
        else if (!strcmp(argv[i], "--mitm-space-cap")) g_cap_space = atof(argv[++i]);
        else if (!strcmp(argv[i], "--mitm-right-cap")) g_cap_right = atof(argv[++i]);''')
sub("(limits: space 6e16, right 5e9, case budget %ld) words=%d\\n\", g_mitm_space, g_mitm_left, g_mitm_right, maxcases", "(limits: space %.3g, right %.3g, case budget %ld) words=%d\\n\", g_mitm_space, g_mitm_left, g_mitm_right, g_cap_space, g_cap_right, maxcases")
open(p, "w").write(s)
