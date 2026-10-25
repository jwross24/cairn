#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/zf6900
nice -n 10 ./zfsieve6900 6900 $2 $3 > chunks/c$1.surv.part 2> chunks/c$1.err && mv chunks/c$1.surv.part chunks/c$1.surv
