#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport-shadow480w
date +%s > shadow/neg_start.epoch
nice -n 10 $B/cport_shadow480w shadow480 --lattice $B/data/lattice96.txt --utable shadow/utable_inflated_400.txt --levelprimes $B/data/levelprimes480.txt --cases shadow/cases.txt --only shadow/only.txt --tsv shadow/s480w_neg.tsv > shadow/s480w_neg.txt 2> shadow/s480w_neg.err
date +%s > shadow/neg_end.epoch
