#!/bin/sh
# render.sh <skin> <out.png> [t] [sel] [list] [vol] [prev]  — real ReChord engine
R=$(dirname "$0")/../.build/render_skin
ROOT=$(dirname "$0")/../STEP-2-THEME/.rechord/themes
"$R" "$ROOT" neon-drive "$1" /tmp/_r.ppm "${3:-1000}" "${4:-0}" "${5:-none}" "${6:--14}" "${7:-0}" ${8} && \
python3 -c "import sys;from PIL import Image;Image.open('/tmp/_r.ppm').save(sys.argv[1])" "$2"
