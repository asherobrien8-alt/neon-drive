#!/bin/sh
# Build devsim: the real Neon Drive AP firmware compiled for Linux/x86-64,
# with the real Core B image (bb_core.bin) running in unicorn.
#   needs: cc, make, gcc-arm-none-eabi, python3 + `pip install unicorn`, ffmpeg
#   run ../../firmware/build.sh once first (it prepares .rechord-src)
set -e
H=$(cd "$(dirname "$0")" && pwd)
F=${F:-$H/../../firmware/.rechord-src/firmware}
(cd "$F/.." && make >/dev/null)
cp "$F/../build/cfw/bbcore/bb_core.bin" "$H/"
cd "$H" && make F="$F"
[ -d library ] || sh make_library.sh
echo "devsim ready: sh regress.sh   (or ./mk.sh s3 && sh run.sh s3.txt)"
