#!/bin/zsh
cd /private/tmp/persist-cport
C=./c/cport
A=(--lattice lattice96.txt --cases cases_0545.txt --only only.txt --depth 1)
nice -n 10 $C deepcut $A --eager > logs/c_deepcut_eager.txt 2> logs/c_deepcut_eager.err
echo "eager vs lazy diff lines: $(diff <(grep '^s=' logs/c_deepcut.txt) <(grep '^s=' logs/c_deepcut_eager.txt) | wc -l)"
tail -1 logs/c_deepcut_eager.err
nice -n 10 $C deepcut $A --break lz5 > logs/c_deepcut_break_lz5.txt 2>/dev/null
nice -n 10 $C deepcut $A --break t2 > logs/c_deepcut_break_t2.txt 2>/dev/null
nice -n 10 $C deepcut $A --break v2 > logs/c_deepcut_break_v2.txt 2>/dev/null
nice -n 10 $C deepcut $A --sound > logs/c_deepcut_sound.txt 2>/dev/null
for b in lz5 t2 v2 sound; do
  echo "$b: CLOSED=$(grep -c ' CLOSED' logs/c_deepcut_break_$b.txt 2>/dev/null) difflines=$(diff <(grep '^s=' logs/c_deepcut.txt) <(grep '^s=' logs/c_deepcut_break_$b.txt 2>/dev/null) | grep -c '^>')"
done
echo "sound: CLOSED=$(grep -c ' CLOSED' logs/c_deepcut_sound.txt) difflines=$(diff <(grep '^s=' logs/c_deepcut.txt) <(grep '^s=' logs/c_deepcut_sound.txt) | grep -c '^>')"
