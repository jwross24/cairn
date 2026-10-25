#!/bin/zsh
# fullgate.sh <candidate-dir> <label>
T=/private/tmp/persist-pydesc
C=$1; LB=$2
for s in 72 224 10800; do $T/tools/difft.sh $C $s "$(cat $T/known$s.txt)" $T/logs/${LB}_difftest_$s.log; done
for s in 14336 72 224; do (cd $T && ./py tools/rv.py $C $s 3 gold/${LB}_$s.txt > logs/${LB}_rv_$s.log 2>&1; cmp gold/prod_$s.txt gold/${LB}_$s.txt > logs/${LB}_cmp_$s.log 2>&1; echo "cmp rc=$?" >> logs/${LB}_cmp_$s.log); done
(cd $T && ./py tools/trees_row.py $C $T/gold/${LB}_trees.jsonl > logs/${LB}_trees.log 2>&1; cmp gold/prod_trees.jsonl.norm gold/${LB}_trees.jsonl.norm > logs/${LB}_cmp_trees.log 2>&1; echo "cmp rc=$?" >> logs/${LB}_cmp_trees.log)
$T/tools/gate.sh $C ${LB}_fast --fast --jobs 2
echo done > $T/logs/${LB}_FULLGATE_DONE
