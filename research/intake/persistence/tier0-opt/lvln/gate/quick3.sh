#!/bin/bash
# usage: quick3.sh <binary> [ref]: compare raw stdout+stderr with cached frozen-reference outputs on every saved (cfg,parents)
R=/private/tmp/persist-lvln; BIN=$1; same=0; diff=""
for c in $R/bench2/*/*/cfgL*.txt; do d=$(dirname $c); n=$(basename $(dirname $d))_$(basename $d); L=$(basename $c .txt | sed 's/cfg//'); P=$d/parents${L#L}.txt
  if [ ! -f $R/refout2/$n.$L.out ]; then nice -n 10 $R/base/lvlN $c $P > $R/refout2/$n.$L.out 2> $R/refout2/$n.$L.err; fi
  [ "$BIN" = ref ] && continue
  timeout 300 $BIN $c $P > $R/logs/qc.out 2> $R/logs/qc.err
  if cmp -s $R/refout2/$n.$L.out $R/logs/qc.out && cmp -s $R/refout2/$n.$L.err $R/logs/qc.err; then same=$((same+1)); else diff="$diff $n/$L"; fi
done; echo "$BIN: same=$same diff=[$diff]"
