#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport-shadow480w
date +%s > shadow/start.epoch
/usr/bin/time -l nice -n 10 $B/cport_shadow480w shadow480 --lattice $B/data/lattice96.txt --utable $B/data/utable_u2.txt --levelprimes $B/data/levelprimes480.txt --cases shadow/cases.txt --only shadow/only.txt --tsv shadow/s480w.tsv > shadow/s480w.txt 2> shadow/s480w.err
date +%s > shadow/end.epoch
