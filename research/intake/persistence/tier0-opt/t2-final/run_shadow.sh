#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport-shadow480w
T=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/t2-final
U=$1
TAG=$2
cd $T
nice -n 10 $B/cport_shadow480w shadow480 --lattice $B/data/lattice96.txt --utable $U --levelprimes $B/data/levelprimes480.txt --cases shadow/cases.txt --only shadow/only.txt --tsv shadow/$TAG.tsv > shadow/$TAG.log 2>&1
echo "rc=$?" >> shadow/$TAG.log
