# Idea (b): meet-in-the-middle / Wagner on Delta with the mod-73 condition as the join key

The shipped join (join24swap/lvlN.c) is already a two-list meet-in-the-middle whose key is prime 73 alone (K = 2 allowed residues) or the pair (73,137) (K = 68),
chosen per parent by a cost model. Variants measured here: every key set forced (JOIN_FORCE_SET 0..4 on src/lane2_mut), see RESULT.md.
Wagner's k-tree is not a complete enumerator: at each level it keeps, for a fixed intermediate target, only the pairs that hit it, so it returns a sample of solutions;
the survivor sets must be byte-identical, so it is recorded as not implementable. A complete 3- or 4-list tree keeps all n^2 pair sums and is the two-list join with a lazily
summed outer list (lift-ideation lane: meet operations x1.2 of the two-list join, slope 0.48-0.67 not 1/3).
