#!/bin/sh
# Build simulator/index.html — one self-contained page (no server needed).
#   needs: python3, node/npm, and `pip install ziglang==0.13.0` (C -> WebAssembly)
#   the page embeds the WebAssembly build plus a wasm2js copy for browsers or
#   pages whose security policy blocks WebAssembly
#   run firmware/build.sh once first (it prepares the patched ReChord source)
set -e
S=$(cd "$(dirname "$0")" && pwd)
R="$S/.."
F="$R/firmware/.rechord-src/firmware"
[ -d "$F" ] || { echo "run firmware/build.sh first"; exit 1; }
[ -d "$S/node_modules" ] || (cd "$S" && npm install --silent)
CC="python3 -m ziglang cc"
SRCS="$F/ui/ui.c $F/ui/settings_schema.c $F/ui/settings_view.c $(ls $F/ui/screens/*.c)
 $F/theme/theme.c $F/theme/themes_builtin.c $F/theme/theme_pkg.c $F/theme/theme_file.c
 $F/theme/theme_runtime.c $F/theme/theme_assets.c $F/theme/theme_skin.c
 $F/drivers/display.c $F/drivers/panel_init_rknanoc.c $F/drivers/font.c $F/drivers/font8x8.c
 $F/drivers/panel_io_sim.c $F/services/media_db.c $F/services/media_query.c $F/services/scratch.c
 $F/services/fs_host.c $F/services/settings.c $F/services/settings_fs.c
 $F/services/eq_profile.c $F/services/art_pack.c $F/services/library_extras.c
 $F/services/file_io.c $F/services/bt_proto.c $F/startup/neon_fx.c"
mkdir -p "$S/.build"
$CC -target wasm32-wasi -mexec-model=reactor -Oz -DSIM_WASM -DFS_HOST_HAVE_DIRENT \
  -include dirent.h -include sys/stat.h -w -std=gnu99 \
  -I$F -I$F/ui -I$F/services -I$F/player -I$F/drivers \
  "$S/sim_main.c" "$S/sim_player.c" "$S/sim_bt.c" $SRCS -o "$S/.build/sim.wasm"
T="$R/firmware/.rechord-src/themes"
python3 "$S/pack_page.py" "$S/.build/sim.wasm" "$S/index.html" \
  "$R/STEP-2-THEME/.rechord=Internal/.rechord" \
  "$T/cassette=Internal/.rechord/themes/cassette" \
  "$T/companion-bot=Internal/.rechord/themes/companion-bot"
