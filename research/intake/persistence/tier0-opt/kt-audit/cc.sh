#!/bin/zsh
export KT_CFG=$1 KT_OUT=$3
PYTHONPATH=/Library/Developer/CommandLineTools/Library/PrivateFrameworks/LLDB.framework/Resources/Python nice -n 10 /usr/bin/lldb -b \
 -o "command script import $PWD/tally.py" -o "command script add -f tally.armc armc" \
 -o "target create /Users/jwross/Documents/cairn/research/intake/persistence/tier0/lvlN" \
 -o "breakpoint set -n main" -o "process launch -o /dev/null -- $1 $2" -o "armc" -o "continue" -o "script tally.ccdump()" >$3.log 2>&1
