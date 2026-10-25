# Final stage on 9633792 and 116169984 (the two T_2 vertices above the sweep cap)

Labels: a pattern is "closed by the cut" or "closed by the sandwich (U″)". Both are conditional on Lemma C, Matveev, Yu 2007 Theorem II and the pattern list. Nothing is PROVEN.

No-Claim: green here shows the recorded anchored open patterns of these two vertices are closed under the stated conditions. It does not prove the pattern list complete, does not re-verify the Baker tables beyond their recorded provenance, and is not Lean-checked.

## Headline

- Level stage (`tier0-opt/t2-cap/run3.log`, unchanged `tier0/run_trees_c_v2.py`, cap 2.4e13): 9633792 has 2.02e13 patterns and 16,474 open@96 after 13,807 s; 116169984 has 2.34e13 patterns and 7,756 open@96 after 52,185 s. Both are "CLOSED BELOW 10^1.3e+27 DIGITS".
- The listed exceptional entries equal row `open` for both (16,474 and 7,756), and all are anchored 3-tuples `(a, y, sol)`. They repeat per open pattern and collapse to 1,742 and 1,124 distinct anchors `(M, a, y)`, which is exactly the full-key count `final_stage.py` ran on. There are no unanchored open patterns, so there is no RECORD-MISMATCH (unlike 1161216 and 11239424 in final13).
- Lemma C depth 1 closes 1,966 of 2,866 (1,171 + 795); 900 survive (31.4%; predicted 20% [12%, 32%]; final13 23.1%).
- Level-480 shadow (`cport_shadow480w`, `utable_u2.txt`): 900 of 900 closed, 147 by the cut and 753 by the sandwich (U″). The smallest sandwich bound is 10^300.70 digits (9633792) and 10^300.81 digits (116169984). 0 open, 0 NOTAPPL, 0 budget, rc 0, 236 s each.
- Vertex status: every anchored pattern of 9633792 and 116169984 is closed by the cut or by the sandwich (U″).
- PAPER Theorem 2 count: 151 → 153 of 177 (152 without the 3281116734 seam). The only T_2 vertex left is the Tier B 1811939328.

## Controls

- Positive control: `final_stage.py --vertices 2667168,1843968,368947264` gives 3 of 3 vertex lines byte-equal to `cport/FINAL-STAGE-run-U2.txt`.
- Planted negative: the same shadow run with every U set to 10^400 (`final13/shadow/utable_inflated_400.txt`, md5 f32488ec) gives 753 open and 147 CLOSED-cut. The pairing with the true run is exactly (CLOSED-sandwich → open) 753 and (CLOSED-cut → CLOSED-cut) 147. The certificate can refuse.

## Commands

`run_d1.sh` (depth 1 with `--sources ../t2-cap/trees_t2cap.jsonl --deadline-epoch 1`, then the control), `final13/mk_shadow_inputs.py d1 shadow`, `run_shadow.sh <utable> <tag>` for `s480w` and `neg400`. Everything ran under nice 10 with at most 2 processes. Wall times: depth 1 237 s, control 28 s.

## Prediction scoring

| Prediction | Outcome |
|---|---|
| Depth-1 survival 20% [12%, 32%] | 31.4%, inside the interval near its top |
| Shadow closes every survivor (p 0.85) | Yes, 900/900 |
| Bounds from about 10^300 | 10^300.70 minimum |
| Both vertices CLOSED (p 0.8); risk of RECORD-MISMATCH from duplicate 3-tuples | Both closed; duplicates collapse cleanly, no mismatch |
| Under 30 min per stage | 4 min each |

## Seams

- Duplicate-collapse reading: anchored 3-tuples carry no nu/eps, so `final_stage.py` keys them as `s M a y - -` and the deepcut covers every representation of the anchor. This is the same treatment final13 applied to trees_c-format rows; it was not re-derived here.
- No cport sandwich pass was run on the 900 (final13 used it as a second certificate). The shadow alone carries the verdict.

## md5

```
53ed98fe468ccb345fa74aa772827455  PREDICTION.md
e4c481538212631851d82ecbc62a7f4e  ../t2-cap/trees_t2cap.jsonl
528b1ba77f8c692d55b4c4b6a9274e02  d1/pattern_status.json
73275638b578c7309145c7b990f6019c  shadow/s480w.tsv
4d96f85d1216961699c9287ede705a93  shadow/neg400.tsv
e1fc6a5544e95d2f7aae1a3653b37304  ../cport/tools/final_stage.py
b95707a1983b6fc6e5c330d90dcfbdbc  ../cport/cport
8ac5bbd646fd36cec064b45005692d55  ../cport-shadow480w/cport_shadow480w
cd1e4f5092b5b53896d84a214e5cdf04  ../cport-shadow480w/data/utable_u2.txt
```
