#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierb-anchored
for vi in 1 2 3 5 6 7 9 10 11 12; do
  uv run --no-project python -I do_vertex.py $vi 2000 3000 4$vi > work/smp_v${vi}.log 2>&1
  TB_WORKERS=1 TB_BIN=$PWD/bin/cport_cong TB_FLAGS="--word-mitm" nice -n 10 uv run --no-project python -I run_surv.py work/smp_v${vi}_emit.out ../tierc-r2bill/data/utable_u2_k34.txt sv${vi} def > runs/sv${vi}.log 2>&1
  uv run --no-project python -I est_vertex.py $vi > work/est_v${vi}.log 2>&1
done
echo done > work/chain_smp.done
