#!/bin/bash
# usage: ri.sh ITEM PAGE OUTNAME [DPI]
f=$(grep $1 /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-OUT-C13/coder_1/tools/CODER_SHEET.orig.csv | cut -d, -f2)
cd /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-OUT-C13/coder_1/tools && /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python -I render.py /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-OUT-C13/coder_1/src/$f.pdf $2 /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-OUT-C13/coder_1/tools/img/$3.png ${4:-80}
