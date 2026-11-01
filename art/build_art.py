#!/usr/bin/env python3
"""Render the art and convert it to the Echo Mini's raw RGB565 format.

    python3 art/build_art.py      -> STEP-2-THEME/.rechord/themes/neon-drive/img/*.565
                                     art/out/*.png (previews), art/out/sites.json

RGB565 little-endian, row-major, no header (the skin/firmware know the
sizes). A 4x4 ordered dither hides the 16-bit banding in the sky and glows.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT_IMG = os.path.join(ROOT, "STEP-2-THEME", ".rechord", "themes", "neon-drive", "img")
OUT_ART = os.path.join(HERE, "out")

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def to565(img):
    a = np.asarray(img.convert("RGB"), np.float32)
    h, w, _ = a.shape
    t = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]
    r = np.clip(np.floor(a[..., 0] / 255 * 31 + t), 0, 31).astype(np.uint16)
    g = np.clip(np.floor(a[..., 1] / 255 * 63 + t), 0, 63).astype(np.uint16)
    b = np.clip(np.floor(a[..., 2] / 255 * 31 + t), 0, 31).astype(np.uint16)
    return ((r << 11) | (g << 5) | b).astype("<u2").tobytes()


def preview565(data, w, h):
    v = np.frombuffer(data, "<u2").reshape(h, w).astype(np.uint32)
    rgb = np.stack([(v >> 11) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31], -1)
    return Image.fromarray(rgb.astype(np.uint8))


def main():
    os.makedirs(OUT_IMG, exist_ok=True)
    os.makedirs(OUT_ART, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(HERE, "render_city.py"), OUT_ART], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "render_boot.py"), OUT_ART], check=True)
    jobs = [("city.png", "city.565")] + [("holo_%d.png" % i, "holo_%d.565" % i) for i in range(4)] + \
           [("boot_shut.png", "boot_shut.565"), ("boot_open.png", "boot_open.565"),
            ("boot_sign.png", "boot_sign.565")]
    total = 0
    for src, dst in jobs:
        im = Image.open(os.path.join(OUT_ART, src))
        data = to565(im)
        open(os.path.join(OUT_IMG, dst), "wb").write(data)
        preview565(data, *im.size).save(os.path.join(OUT_ART, "dev_" + src))
        total += len(data)
        print("%-16s %4dx%-4d %7d B" % (dst, im.size[0], im.size[1], len(data)))
    # dead-sign patches for the home flicker: 電脳, 拉麺, AKATSUKI stacked in
    # one 55-px-wide strip (rows 0, 24, 48), the city dimmed under them
    import json
    sites = json.load(open(os.path.join(OUT_ART, "sites.json")))["signs"]
    city = Image.open(os.path.join(OUT_ART, "city.png")).convert("RGB")
    strip = Image.new("RGB", (55, 59), (0, 0, 0))
    for (i, row) in ((0, 0), (2, 24), (4, 48)):
        sg = sites[i]
        patch = np.asarray(city.crop((sg["x"], sg["y"], sg["x"] + sg["w"], sg["y"] + sg["h"])), np.float32)
        lum = patch.mean(-1, keepdims=True)
        patch = patch * 0.18 + lum * 0.06          # unlit tube: dark, desaturated
        strip.paste(Image.fromarray(np.uint8(np.clip(patch, 0, 255))), (0, row))
    data = to565(strip)
    open(os.path.join(OUT_IMG, "signs_off.565"), "wb").write(data)
    total += len(data)
    print("%-16s %4dx%-4d %7d B" % ("signs_off.565", 55, 59, len(data)))
    print("total %d B on the player" % total)


if __name__ == "__main__":
    main()
