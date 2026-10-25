#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0
for part in $@; do
  PYTHONDONTWRITEBYTECODE=1 nice -n 10 uv run --no-project --with sympy python -I ../tier0-opt/tierb-anchored/ref_check.py ../tier0-opt/tierb-anchored/work/xc_b_part_$part 71663616 > ../tier0-opt/tierb-anchored/work/xc_b_part_$part.ref 2>&1
done
echo done > ../tier0-opt/tierb-anchored/work/chain_ref_$1.done
