#!/bin/sh
# Rebuild STEP-1-FIRMWARE/HIFIEC90.IMG from source.
#
# ReChord (https://github.com/brnomt/FiioDcomp) at a pinned commit + the
# Neon Drive patch: theme engine extras (scaled/transparent text, styled
# lists, transparent/mirrored sprites, "menu" home action, battery in skins)
# plus Search, A-Z jump, playlists, faster loading, smoother playback,
# extra EQ presets and the boot / power-off animations. Linux/macOS/WSL:
#
#   sudo apt install gcc-arm-none-eabi python3 git make
#   sh firmware/build.sh
set -e
BASE=70ae40faf22e001211b2647c6fdaedf0a9128ffb
HERE=$(cd "$(dirname "$0")" && pwd)
WORK="$HERE/.rechord-src"

if [ ! -d "$WORK/.git" ]; then
    git clone https://github.com/brnomt/FiioDcomp.git "$WORK"
fi
cd "$WORK"
git fetch -q origin
git checkout -q -f "$BASE"
git clean -qfd firmware
git apply "$HERE/neon-drive-engine.patch"

# upstream host tests must still pass with the patch
sh firmware/ui/tests/run_tests.sh       | tail -1
sh firmware/theme/tests/run_tests.sh    | tail -1
sh firmware/services/tests/run_tests.sh | tail -1

make
cp build/ReChord_AP5M.IMG "$HERE/../STEP-1-FIRMWARE/HIFIEC90.IMG"
echo "built: STEP-1-FIRMWARE/HIFIEC90.IMG"
sha256sum "$HERE/../STEP-1-FIRMWARE/HIFIEC90.IMG" 2>/dev/null || shasum -a 256 "$HERE/../STEP-1-FIRMWARE/HIFIEC90.IMG"
