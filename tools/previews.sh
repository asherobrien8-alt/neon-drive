#!/bin/sh
# Regenerate docs/preview/* from the real engine.
set -e
cd "$(dirname "$0")/.."
R=.build/render_skin; T=STEP-2-THEME/.rechord/themes; O=docs/preview; S=$(mktemp -d)
mkdir -p $O
png() { $R $T neon-drive "$1" $S/x.ppm $3 $4 $5 $6 $7 $8 && python3 -c "import sys;from PIL import Image;Image.open(sys.argv[1]).resize((640,340),Image.NEAREST).save(sys.argv[2])" $S/x.ppm "$O/$2.png"; }
png home.skin home 900 1
png now_playing.skin now_playing 5000 0 none -4 40 -40
png library.skin library 0 1 library
png library_cat.skin songs 0 3 cat
png browser.skin files 0 2 browser
png settings.skin settings 0 2 settings
SEQ=$(python3 -c "
v=[-14]*45
for x in range(-13,-1): v+=[x]*3
v+=[-2]*20
for x in range(-3,-41,-2): v+=[x]*2
v+=[-40]*22
print(','.join(map(str,v)))") $R $T neon-drive now_playing.skin $S/np 1000 0 none -14
SEQ=$(python3 -c "print(','.join(['-14']*48))") STEP=80 $R $T neon-drive home.skin $S/home 0 1 none -14
python3 - "$S" "$O" <<'PY'
import sys, glob
from PIL import Image
S, O = sys.argv[1:]
for name, dur in (("np", 60), ("home", 80)):
    fr = [Image.open(f).convert("RGB").resize((640, 340), Image.NEAREST) for f in sorted(glob.glob(f"{S}/{name}_*.ppm"))]
    q = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in fr]
    out = {"np": "now_playing_volume_runner", "home": "home_live_wallpaper"}[name]
    q[0].save(f"{O}/{out}.gif", save_all=True, append_images=q[1:], duration=dur, loop=0, optimize=True)
PY
rm -rf $S; ls $O
