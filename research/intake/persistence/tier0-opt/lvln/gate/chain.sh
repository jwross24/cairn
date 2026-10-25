#!/bin/bash
R=/private/tmp/persist-lvln
for v in v1 v2 v3 v4 v5 v6 v7 v8 v8pgo; do
  src=$R/$v/lvlN.c; [ $v = v8pgo ] && src=$R/v8/lvlN.c
  bash $R/gate.sh $v $R/$v/lvlN $src
done
