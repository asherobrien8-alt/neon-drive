#!/usr/bin/env python3
"""Compile the Neon Drive skins from src/*.skin into theme/*.skin.

The sources use readable colour names ({pink}, {cyan}...) and comments; the
output is compact, decimal RGB565, and checked against ReChord's engine
limits so a skin can never be rejected on the device:

  4096 bytes per skin, 64 sections (incl. [skin]/[vars]; Neon Drive raised it from 52), 12 props/section, 144-byte values,
  20 vars total, 112-byte var expressions.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "STEP-2-THEME", ".rechord", "themes", "neon-drive")

PALETTE = {
    # UI
    "navy":     "#110d1f",   # background
    "panel":    "#1d1833",   # surface
    "white":    "#eef4ff",
    "dim":      "#8a86b0",
    "faint":    "#3a3358",
    "cyan":     "#3ff0e0",
    "cyan_dk":  "#1d8a82",
    "red":      "#ff3b4f",
    "lime":     "#b6ff5a",
    "purple":   "#4b2f86",
    # scene
    "sky_top":  "#07041a",
    "sky_mid":  "#3b0f55",
    "sun_hi":   "#ffd54a",
    "sun_or":   "#ff8a3c",
    "sun":      "#ff3f6c",
    "ground":   "#12061c",
    "road":     "#26092f",
    "pink":     "#ff3fbf",
    "grid":     "#9c1f86",
    "mtn":      "#1c0a30",
    "car":      "#8a7ca8",
    "car_dk":   "#2a1d3f",
    "tail":     "#ff2040",
    "star":     "#c9b8ff",
    # home city (v2)
    "sky":      "#0d0a1c",
    "tag":      "#ff2a3c",
    "tag_dim":  "#7a1424",
    "ring1":    "#ff5a4a",
    "ring2":    "#9a2a3a",
    "ring3":    "#3a1424",
    "bldg":     "#231d3d",
    "bldg2":    "#2c2450",
    "rim":      "#ff7a4a",
    "win_y":    "#ffd27a",
    "win_c":    "#8fe8ff",
    "win_p":    "#ff6fae",
    "street":   "#151030",
    # runner
    "camo":     "#5f7f68",
    "glow":     "#1f6f68",
    "shoe":     "#b6ff5a",
}


def rgb565(hexc):
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


COL = {k: str(rgb565(v)) for k, v in PALETTE.items()}


def compile_skin(text, name):
    out, sections, props, nvars = [], 0, 0, 0
    cur = None
    for raw in text.split("\n"):
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"\{(\w+)\}", lambda m: COL[m.group(1)], line)
        if line.startswith("["):
            cur = line[1:-1]
            sections += 1          # the engine counts every [section]
            props = 0
            out.append(line)
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        props += 1
        assert props <= 12, "%s [%s]: >12 props" % (name, cur)
        assert len(v) <= 144, "%s [%s] %s: value too long" % (name, cur, k)
        if cur and cur.startswith("vars"):
            nvars += 1
            assert len(v) <= 112, "%s var %s: expr %d > 112" % (name, k, len(v))
        out.append("%s=%s" % (k, v))
    blob = "\n".join(out) + "\n"
    assert sections <= 64, "%s: %d sections" % (name, sections)
    assert nvars <= 20, "%s: %d vars" % (name, nvars)
    assert len(blob) <= 4096, "%s: %d bytes > 4096" % (name, len(blob))
    return blob, sections, nvars


LISTS = {
    # out file: (heading expr, list source, vertical word, word colour, footer)
    "library.skin":     ('"LIBRARY"', "library", "MUSIC", "red", '"VOL MOVE  PLAY OPEN  BACK"'),
    "library_cat.skin": ("heading", "category", "INDEX", "pink", '"PLAY OPEN  HOLD PLAY = A-Z"'),
    "browser.skin":     ("heading", "browser", "FILES", "cyan", '"VOL MOVE  PLAY OPEN  BACK"'),
}


def vword(word, col):
    out = []
    for i, ch in enumerate(word):
        out.append("[w%d]\ntype=text\nx=296\ny=%d\ntext=\"%s\"\nscale=2\n"
                   "color={%s}\n" % (i, 28 + i * 24, ch, col))
    return "\n".join(out)


def sources():
    for fn in sorted(os.listdir(SRC)):
        if fn.startswith("_"):
            continue
        yield fn, open(os.path.join(SRC, fn)).read()
    tpl = open(os.path.join(SRC, "_list.tpl")).read()
    for fn, (head, src, word, col, hint) in LISTS.items():
        yield fn, (tpl.replace("@HEAD@", head).replace("@SRC@", src).replace("@HINT@", hint)
                   .replace("@WORD@", vword(word, col)))


def main():
    os.makedirs(OUT, exist_ok=True)
    for fn, src in sources():
        if fn.endswith(".skin"):
            blob, s, v = compile_skin(src, fn)
            print("%-18s %4d B  %2d sections  %2d vars" % (fn, len(blob), s, v))
        else:  # theme.cfg: colour substitution only
            blob = re.sub(r"\{(\w+)\}", lambda m: "0x%04X" % int(COL[m.group(1)]), src)
        open(os.path.join(OUT, fn), "w").write(blob)


if __name__ == "__main__":
    main()
