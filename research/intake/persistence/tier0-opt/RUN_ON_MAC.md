# Running Tier 1 of vertex 1161216 on the Mac (engine v2 + C level-12 pass)

From a plain terminal (not the Cairn session), in the repo:

    cd ~/Documents/cairn/research/intake/persistence/tier0
    uv venv .venv && source .venv/bin/activate && uv pip install gmpy2 sympy
    cc -O3 -march=native -o lvl12 lvl12.c
    # sanity: the 53-vertex validation set must reproduce (≈2 min)
    python3 run_vertex_c.py 72 98,189,294,1161216 $(sysctl -n hw.ncpu) | tail -1
    #   expect: children [98, 189, 294, 1161216], open_patterns 0, complete true
    # the real job (≈1e13 patterns ≈ 180 core-hours at 66 ns/pattern):
    nohup python3 run_vertex_c.py 1161216 128421199872 $(sysctl -n hw.ncpu) > t1_1161216.jsonl 2> t1_1161216.log &

`t1_1161216.log` prints one line per multiset (118 total, smallest first) with CLOSED/OPEN and
timing; `t1_1161216.jsonl` holds the per-multiset record (survivors per level, children,
certified digit bound for each open pattern). The last line is the vertex summary. Anything
other than `children [128421199872]` is a finding to look at before believing it.

What it proves if it finishes with open_patterns 0 and children [128421199872]: the only child
of 1161216 is 128421199872, unconditionally. With open patterns: the same below the printed
digit bound (~10^27). Either way, the next vertex (128421199872, 925 multisets, 10^17 patterns)
is out of reach of this engine and needs an idea, not a bigger machine.

## The bigger job: every vertex of all four trees below 2×10^13 patterns

`zf_below_1e4000.txt` is the verified list of all 8,807 zero-free 2^a 3^b 7^c below 10^4000
(the control corpus and the source of every "known child"). `run_trees_c.py` walks every
vertex of A_2/A_4/A_6/A_8 in increasing pattern count, skipping any vertex already recorded in
the jsonl files you pass as skip lists. The chat session is running the region below 3×10^11
patterns tonight (76 vertices) and will hand you `trees_c.jsonl`; run the rest:

    nohup python3 run_trees_c.py zf_below_1e4000.txt trees_mac.jsonl $(sysctl -n hw.ncpu) 2e13 \
        runall_final.jsonl trees_c.jsonl > /dev/null 2> trees_mac.log &

That is ~110 vertices and ~3×10^14 patterns ≈ 5,500 core-hours at 66 ns/pattern — too much for
one machine in one night; it will chew through the cheap end first (the log is in increasing
order) and you can stop it any time; every finished vertex is already written. Expected final
frontier: about 18 vertices at 10^15–10^22 patterns, which no enumeration will reach. Their
names, with their known children, are the exact statement of what remains open for the even
targets after this program:
  A_6: 71663616, 226492416, 169869312, 1792336896, 13884223438848, 2113929216, 11329339392,
       4444263936, 3699376128, 3416267673274176, 913217421312, 1438916737499136
  A_8: 1194891264, 4182119424, 1783627776, 727326941773824, 112717121716224
  A_2: 1811939328
  A_4: 128421199872
