#!/usr/bin/env python3
"""Neon Drive boot scene (original art): a little Japanese shop in a rainy
alley at night. The firmware rolls the shutter up (revealing boot_open rows),
then flickers the neon sign on (boot_sign = the lit sign window).

Geometry at 320x170 (must match firmware/startup/neon_fx.c):
  door  x 104..215  y 74..143   (w 112, h 70)
  sign  x  96..223  y 26..59    (w 128, h 34)
"""
import os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 4
W, H = 320 * S, 170 * S
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
DOOR = (104, 74, 112, 70)
SIGN = (96, 26, 128, 34)
rng = random.Random(88)


def f(px):
    return ImageFont.truetype(JP, px, index=0)


def rgb(h):
    return tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def bloom(img, radius, k):
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), np.float32) * k


def base_scene(open_shop):
    im = Image.new("RGB", (W, H), rgb("#07060f"))
    d = ImageDraw.Draw(im)
    # sky slit between buildings + far glow
    d.rectangle([0, 0, W, 20 * S], fill=rgb("#120a26"))
    # left & right buildings (alley walls)
    d.rectangle([0, 0, 70 * S, H], fill=rgb("#120e22"))
    d.rectangle([250 * S, 0, W, H], fill=rgb("#120e22"))
    d.rectangle([70 * S, 0, 74 * S, H], fill=rgb("#1d1736"))
    d.rectangle([246 * S, 0, 250 * S, H], fill=rgb("#1d1736"))
    # shop building facade
    d.rectangle([84 * S, 10 * S, 236 * S, 150 * S], fill=rgb("#1a1530"))
    d.rectangle([84 * S, 10 * S, 236 * S, 12 * S], fill=rgb("#2e2650"))
    # awning
    d.polygon([(92 * S, 66 * S), (228 * S, 66 * S), (234 * S, 72 * S), (86 * S, 72 * S)], fill=rgb("#3a1020"))
    for k in range(10):
        x = 92 * S + k * 14 * S
        d.rectangle([x, 66 * S, x + 7 * S, 71 * S], fill=rgb("#5a1828"))
    # door frame
    dx, dy, dw, dh = DOOR
    d.rectangle([(dx - 3) * S, (dy - 2) * S, (dx + dw + 3) * S, (dy + dh + 1) * S], fill=rgb("#0c0a18"))
    if open_shop:
        # warm interior: counter, shelves, lanterns, menu boards
        d.rectangle([dx * S, dy * S, (dx + dw) * S, (dy + dh) * S], fill=rgb("#4a2a24"))
        d.rectangle([dx * S, dy * S, (dx + dw) * S, (dy + 30) * S], fill=rgb("#5e3828"))
        for k in range(4):   # shelves with bottles
            y = (dy + 8 + k * 7) * S
            d.rectangle([(dx + 6) * S, y, (dx + 50) * S, y + S], fill=rgb("#2a1610"))
            for j in range(9):
                c = rng.choice([rgb("#ffcf7a"), rgb("#7affd8"), rgb("#ff7aa8"), rgb("#c8a0ff")])
                d.rectangle([(dx + 7 + j * 5) * S, y - 4 * S, (dx + 9 + j * 5) * S, y - S], fill=c)
        for k in range(5):   # menu boards
            x = (dx + 58 + k * 10) * S
            d.rectangle([x, (dy + 6) * S, x + 8 * S, (dy + 22) * S], fill=rgb("#f2e6c8"))
            d.text((x + S, (dy + 7) * S), "麺酒茶丼餃"[k], font=f(6 * S), fill=rgb("#3a1a10"))
        d.rectangle([dx * S, (dy + 44) * S, (dx + dw) * S, (dy + 52) * S], fill=rgb("#2a160e"))  # counter
        d.rectangle([dx * S, (dy + 44) * S, (dx + dw) * S, (dy + 45) * S], fill=rgb("#ffb070"))
        for k in range(5):   # stools
            x = (dx + 10 + k * 22) * S
            d.rectangle([x, (dy + 56) * S, x + 8 * S, (dy + 58) * S], fill=rgb("#d03040"))
            d.rectangle([x + 3 * S, (dy + 58) * S, x + 5 * S, (dy + dh) * S], fill=rgb("#201010"))
        for k in range(3):   # lanterns inside
            cx = (dx + 22 + k * 34) * S
            d.ellipse([cx - 5 * S, (dy + 26) * S, cx + 5 * S, (dy + 38) * S], fill=rgb("#ff5040"))
    else:
        # corrugated roll-up shutter + graffiti + padlock
        for y in range(dy * S, (dy + dh) * S, 3 * S):
            d.rectangle([dx * S, y, (dx + dw) * S, y + 2 * S], fill=rgb("#4a4f66"))
            d.rectangle([dx * S, y + 2 * S, (dx + dw) * S, y + 3 * S], fill=rgb("#2a2d40"))
            d.rectangle([dx * S, y, (dx + dw) * S, y + S // 2], fill=rgb("#6a7090"))
        d.text(((dx + 22) * S, (dy + 26) * S), "NEO", font=f(14 * S), fill=rgb("#c04090"))
        d.text(((dx + 64) * S, (dy + 30) * S), "夜", font=f(12 * S), fill=rgb("#40a0b0"))
        d.rectangle([(dx + 52) * S, (dy + dh - 6) * S, (dx + 60) * S, (dy + dh - 1) * S], fill=rgb("#c8a040"))
    # sign box (unlit by default)
    sx, sy, sw, sh = SIGN
    d.rectangle([sx * S, sy * S, (sx + sw) * S, (sy + sh) * S], fill=rgb("#0b0816"))
    d.rectangle([sx * S, sy * S, (sx + sw) * S, (sy + sh) * S], outline=rgb("#2a2440"), width=S)
    d.text(((sx + 8) * S, (sy + 1) * S), "電源オン", font=f(25 * S), fill=rgb("#2a1a2c"))
    # vending machine (left), glowing
    d.rectangle([38 * S, 82 * S, 66 * S, 146 * S], fill=rgb("#e8f2ff"))
    d.rectangle([40 * S, 86 * S, 64 * S, 118 * S], fill=rgb("#1a3a6a"))
    for r in range(3):
        for c in range(4):
            col = rng.choice([rgb("#ff5050"), rgb("#ffd050"), rgb("#50d0ff"), rgb("#60ff90")])
            d.rectangle([(42 + c * 6) * S, (89 + r * 10) * S, (45 + c * 6) * S, (95 + r * 10) * S], fill=col)
    # paper lanterns (right)
    for k, y in enumerate((60, 86)):
        d.ellipse([256 * S, y * S, 270 * S, (y + 18) * S], fill=rgb("#ff4030"))
        d.text((258 * S, (y + 3) * S), "祭"[0], font=f(10 * S), fill=rgb("#2a0808"))
    # power lines
    for k in range(3):
        y0 = (6 + k * 5) * S
        d.line([(0, y0), (W // 2, y0 + 9 * S), (W, y0 + 2 * S)], fill=rgb("#05040a"), width=S // 2 + 1)
    # wet street
    d.rectangle([0, 146 * S, W, H], fill=rgb("#0b0a16"))
    a = np.asarray(im, np.float32)
    # glows: vending machine, lanterns, interior
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.rectangle([38 * S, 82 * S, 66 * S, 146 * S], fill=(120, 170, 255))
    g.ellipse([256 * S, 60 * S, 270 * S, 78 * S], fill=(255, 70, 40))
    g.ellipse([256 * S, 86 * S, 270 * S, 104 * S], fill=(255, 70, 40))
    if open_shop:
        g.rectangle([dx * S, dy * S, (dx + dw) * S, (dy + dh) * S], fill=(255, 150, 80))
    a += bloom(glow, 12 * S, 0.55)
    # street reflections
    refl = a[146 * S - (H - 146 * S):146 * S][::-1] * 0.35
    a[146 * S:] = a[146 * S:] * 0.65 + refl[:H - 146 * S]
    # rain
    rain = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rain)
    r2 = random.Random(5)
    for _ in range(320):
        x, y = r2.randrange(W), r2.randrange(H)
        rd.line([(x, y), (x - 2 * S, y + 8 * S)], fill=60, width=1)
    a += np.asarray(rain, np.float32)[..., None] * np.array([0.6, 0.7, 1.0])
    return Image.fromarray(np.uint8(np.clip(a, 0, 255)))


def lit_sign(scene):
    sx, sy, sw, sh = SIGN
    tube = Image.new("RGB", (W, H), (0, 0, 0))
    t = ImageDraw.Draw(tube)
    t.text(((sx + 8) * S, (sy + 1) * S), "電源オン", font=f(25 * S), fill=rgb("#ff3fbf"))
    t.rectangle([sx * S, sy * S, (sx + sw) * S, (sy + sh) * S], outline=rgb("#3ff0e0"), width=S)
    a = np.asarray(scene, np.float32)
    tb = np.asarray(tube, np.float32)
    a = np.where(tb.sum(-1, keepdims=True) > 0, tb * 0.6 + 255 * 0.4 * (tb > 0), a)
    a += bloom(tube, 3 * S, 1.2) + bloom(tube, 10 * S, 0.8)
    im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    small = im.resize((320, 170), Image.LANCZOS)
    return small.crop((sx, sy, sx + sw, sy + sh))


def main():
    shut = base_scene(False)
    opened = base_scene(True)
    shut.resize((320, 170), Image.LANCZOS).save(os.path.join(OUT, "boot_shut.png"))
    opened.resize((320, 170), Image.LANCZOS).save(os.path.join(OUT, "boot_open.png"))
    lit_sign(opened).save(os.path.join(OUT, "boot_sign.png"))
    # preview of the final frame
    fin = opened.resize((320, 170), Image.LANCZOS)
    fin.paste(Image.open(os.path.join(OUT, "boot_sign.png")), (SIGN[0], SIGN[1]))
    fin.resize((640, 340), Image.LANCZOS).save(os.path.join(OUT, "boot_final_2x.png"))
    shut.resize((640, 340), Image.LANCZOS).save(os.path.join(OUT, "boot_shut_2x.png"))


if __name__ == "__main__":
    main()
