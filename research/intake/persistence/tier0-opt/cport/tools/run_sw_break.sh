#!/bin/zsh
cd /private/tmp/persist-cport
C=./c/cport
A=(--lattice lattice96.txt --utable utable.txt --cases cases_0545.txt --only survivors.txt)
nice -n 10 $C sandwich $A --break nearest --tsv logs/c_sandwich_break_nearest.tsv > logs/c_sandwich_break_nearest.txt 2>/dev/null
nice -n 10 $C sandwich $A --break lz5 --tsv logs/c_sandwich_break_lz5.tsv > logs/c_sandwich_break_lz5.txt 2>/dev/null
nice -n 10 $C sandwich $A --break t2 --tsv logs/c_sandwich_break_t2.tsv > logs/c_sandwich_break_t2.txt 2>/dev/null
nice -n 10 $C sandwich $A --sound --tsv logs/c_sandwich_sound.tsv > logs/c_sandwich_sound.txt 2>/dev/null
for b in nearest lz5 t2; do
  echo "$b: lines differing from faithful run: $(diff <(grep '^s=' logs/c_sandwich.txt | sed 's/ \[[0-9]*s\]$//') <(grep '^s=' logs/c_sandwich_break_$b.txt | sed 's/ \[[0-9]*s\]$//') | grep -c '^>')"
  tail -1 logs/c_sandwich_break_$b.txt
done
echo "sound: lines differing: $(diff <(grep '^s=' logs/c_sandwich.txt | sed 's/ \[[0-9]*s\]$//') <(grep '^s=' logs/c_sandwich_sound.txt | sed 's/ \[[0-9]*s\]$//') | grep -c '^>')"
tail -1 logs/c_sandwich_sound.txt
