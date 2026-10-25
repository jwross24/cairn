# Idea (e): counting DP + backtracking that enumerates only passing children

Code: ideaE/e_dp.inc, switch `LANE2_E=1` (key prime 73, 73 states in one 128-bit word). Backward DP: Q_S = (allowed set of key residues) - base; Q_s = union over k of Q_{s+1} - contrib(s,k);
depth-first search over the slots visiting a prefix only if its running key residue lies in Q_{prefix}; every leaf is a candidate of the join with key 73. Leaves go through the same
prefilter/full test. Slot orders LANE2_EORD = 0/1/2. Identical outputs on 228/228; slower than join24 (RESULT.md).
