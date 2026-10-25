#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierb-anchored
nice -n 10 ./enum_surv2 10 5 5 emit 31 0.1 < work/triples_v4.txt > work/full_v4_emit.out 2> work/full_v4.err
nice -n 10 ./enum_surv2 26 3 0 emit 32 0.02 < work/triples_v8.txt > work/full_v8_emit.out 2> work/full_v8.err
echo chain-done > work/chain_full.done
