#!/bin/zsh
cd /private/tmp/persist-cport
C=./c/cport
L=(--lattice lattice96.txt)
nice -n 10 $C deepcut $L --cases cases_all.txt --only only_all.txt --depth 4 --maxcases 2000000 > logs/a_f4.txt 2>/dev/null
nice -n 10 $C deepcut $L --cases cases_all.txt --only only_all.txt --depth 4 --maxcases 2000000 --sound > logs/a_s4.txt 2>/dev/null
echo done > logs/sound4.done
