import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(HERE, "..", "..", "..", "tier0", "lvlN.c")).read()
helper = open(os.path.join(HERE, "src", "measure_helper.inc")).read()


def rep(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new, 1)


s = src
s = rep(s, "if(g==ng){ process_child(); return; }", "if(g==ng){ measure_child(); return; }")
s = rep(s, "// enumerate children: per digit group", helper + "\n// enumerate children: per digit group")
s = rep(s, "read_cfg(argv[1]); lazy_init(); batch_init();", "read_cfg(argv[1]); lazy_init(); batch_init(); meas_init(); meas_env();")
s = rep(
    s,
    "    pidx_cur=pidx; a_cur=a; parent_init();\n    for(int dn=0;dn<2;dn++)",
    "    pidx_cur=pidx; a_cur=a; if(!meas_take_parent(pidx)){ pidx++; continue; }\n    parent_init();\n    for(int dn=0;dn<2;dn++)",
)
idx = s.rfind('fprintf(stderr,"parents %d children')
s = s[:idx] + "meas_report();\n  " + s[idx:]
open(os.path.join(HERE, "src", "measure.c"), "w").write(s)
print("ok")
