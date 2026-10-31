#!/bin/sh
# Build the host renderer (real ReChord engine -> PNG). Run firmware/build.sh once first.
set -e
HERE=$(cd "$(dirname "$0")/.." && pwd); F="$HERE/firmware/.rechord-src/firmware"
mkdir -p "$HERE/.build"
cd "$F" && cc -std=gnu99 -O1 -w -I. -Iui -Iui/internal -Iservices -Iplayer \
  -o "$HERE/.build/render_skin" "$HERE/tools/render_skin.c" \
  theme/theme.c theme/themes_builtin.c theme/theme_pkg.c theme/theme_file.c \
  theme/theme_runtime.c theme/theme_assets.c theme/theme_skin.c \
  drivers/display.c drivers/panel_init_rknanoc.c drivers/font.c drivers/font8x8.c \
  drivers/panel_io_sim.c -lm
echo "renderer: .build/render_skin"
