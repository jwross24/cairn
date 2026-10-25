#!/bin/zsh
S=/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad
for e in 9437184_22222222222222222266 9437184_222222222222222222229; do for L in 48 24; do
 d=$S/h12/$e; ./run_lldb.sh $d/cfgL$L.txt $d/parents$L.txt mech_${e}_$L.json
done; done
echo done > mech.done
