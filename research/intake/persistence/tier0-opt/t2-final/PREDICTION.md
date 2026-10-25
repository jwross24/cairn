# Prediction: final stage on 9633792 and 116169984

Written before any compute in this directory.

Input: `tier0-opt/t2-cap/trees_t2cap.jsonl`, the two T_2 rows from the above-cap sweep (run3.log). Listed anchored entries equal row `open`: 16,474 and 7,756.

Pipeline, identical to `tier0-opt/final13/`:
1. `cport/tools/final_stage.py --sources trees_t2cap.jsonl --vertices 9633792,116169984 --deadline-epoch 1` (Lemma C depth 1 only).
2. `cport-shadow480w/cport_shadow480w shadow480` on the depth-1 survivors, `utable_u2.txt`.
3. Positive control: final_stage on 2667168,1843968,368947264 must be byte-equal on vertex lines to `cport/FINAL-STAGE-run-U2.txt` (as in final13).
4. Planted negative: shadow with `utable_inflated_400.txt` must refuse every sandwich-closed anchor and keep every cut-closed one.

Predictions:
- Depth-1 survival: 20% [12%, 32%] of distinct full keys (final13 23.1%, the 138-vertex run 16.6%).
- Shadow: every survivor closed, 0 open, 0 NOTAPPL, 0 budget. Probability 0.85.
- Bounds from about 10^300 digits upward.
- Both vertices reach CLOSED: probability 0.8. The main risk is a RECORD-MISMATCH from duplicate 3-tuple exceptional entries (same a, y) collapsing to one full key.
- Wall time: depth 1 under 30 min, shadow under 30 min, 2 processes, nice 10.

No-Claim: green here means the recorded anchored open patterns of these two vertices are closed by the cut or by the sandwich (U″), conditional on Lemma C, Matveev, Yu 2007 Thm II and the pattern list. It does not prove the pattern list is complete, nothing is PROVEN, and it is not Lean-checked.
