#!/bin/bash
cd /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-HOLD-C13/coder_1/tools
P="/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python -I view.py"
H=${H:-600}; T=${T:-1600}
for i in "$@"; do echo "######## $i"; NH=${NH:-10} $P $i sum $H $T; f=$(ls ../txt/$(printf %03d $i)_*); echo "-- authors:"; grep -E "delivered by|^ ?[A-Z][A-Za-z .]+, ?C?J\.|\((Oral|ORAL)\)|^ ?Per " -A1 $f | head -4 | tr '\n' ' '; echo; done
