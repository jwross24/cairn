#!/bin/zsh
cd /private/tmp/persist-cport
C=./c/cport
L=(--lattice lattice96.txt)
nice -n 10 $C deepcut $L --cases cases_orig.txt --only only_orig.txt --depth 1 > logs/o_f1.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_orig.txt --only only_orig.txt --depth 1 --sound > logs/o_s1.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_orig.txt --only only_orig.txt --depth 2 > logs/o_f2.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_orig.txt --only only_orig.txt --depth 2 --sound > logs/o_s2.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_all.txt --only only_all.txt --depth 1 > logs/a_f1.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_all.txt --only only_all.txt --depth 1 --sound > logs/a_s1.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_all.txt --only only_all.txt --depth 2 > logs/a_f2.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_all.txt --only only_all.txt --depth 2 --sound > logs/a_s2.txt 2>/dev/null
echo done > logs/sound.done
