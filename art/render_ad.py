#!/usr/bin/env python3
"""Neon Drive battery billboard: two dumb cyberpunk ads for the home
screen's main tower (original art). The firmware shows one for 10 s, hides it
for 10 s, and prints the battery % (plus a bolt while charging) in the dark
strip at the bottom of the ad.

Geometry (must match src/home.skin):
  ad      x 232..281  y 22..79   (50 x 58)
  strip   rows 45..57 of the ad  (the firmware's text/bolt go there)
  bolt    7 x 11
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 6
AW, AH = 50, 58
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
LAT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, px):
    return ImageFont.truetype(path, px, index=0) if path.endswith("ttc") else ImageFont.truetype(path, px)


def rgb(h):
    return tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def glow(im, r, k):
    a = np.asarray(im, np.float32)
    b = np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32)
    return Image.fromarray(np.uint8(np.clip(a + b * k, 0, 255)))


def frame(d, col):
    d.rectangle([0, 0, AW * S - 1, AH * S - 1], outline=rgb(col), width=S)


def strip(d):
    # dark readout strip for the battery number (kept plain so it reads)
    d.rectangle([2 * S, 45 * S, (AW - 2) * S, (AH - 2) * S], fill=rgb("#07050f"))
    d.rectangle([2 * S, 45 * S, (AW - 2) * S, 45 * S + S // 2], fill=rgb("#3ff0e0"))


def ad_cola():
    """SYNTH-COLA: 'now with 0% real ingredients'. Blue/pink diagonal split."""
    im = Image.new("RGB", (AW * S, AH * S), rgb("#1b0d3a"))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (AW * S, 0), (AW * S, 18 * S), (0, 34 * S)], fill=rgb("#1f6fff"))
    for k in range(0, AW * S, 3 * S):               # scanlines on the blue
        d.line([(k, 0), (k - 30 * S, 30 * S)], fill=rgb("#2a7dff"), width=S // 2)
    # the can
    cx, cy = 40 * S, 31 * S
    d.rounded_rectangle([cx - 6 * S, cy - 9 * S, cx + 6 * S, cy + 10 * S], radius=2 * S, fill=rgb("#ff2fa8"))
    d.rectangle([cx - 6 * S, cy - 2 * S, cx + 6 * S, cy + 3 * S], fill=rgb("#fff3fb"))
    d.text((cx, cy + S // 2), "Σ", font=font(LAT, 5 * S), fill=rgb("#ff2fa8"), anchor="mm")
    d.rectangle([cx - 4 * S, cy - 11 * S, cx + 4 * S, cy - 9 * S], fill=rgb("#c8c8e8"))
    # brand
    d.text((3 * S, 3 * S), "SYNTH", font=font(LAT, 9 * S), fill=rgb("#ffffff"))
    d.text((3 * S, 12 * S), "COLA", font=font(LAT, 9 * S), fill=rgb("#ffe14a"))
    d.text((3 * S, 24 * S), "0% REAL", font=font(LAT, 5 * S), fill=rgb("#ffffff"))
    d.text((3 * S, 31 * S), "コーラ", font=font(JP, 7 * S), fill=rgb("#9fe8ff"))
    strip(d)
    frame(d, "#ff2fa8")
    return glow(im, 2 * S, 0.35)


def ad_gum():
    """NEURO-GUM: 'chew your feelings'. Pink halftone with a cyan chip."""
    im = Image.new("RGB", (AW * S, AH * S), rgb("#2a0730"))
    d = ImageDraw.Draw(im)
    for y in range(0, 44 * S, 4 * S):               # halftone dots
        for x in range(0, AW * S, 4 * S):
            r = int((1 - y / (44 * S)) * 1.6 * S) + 1
            d.ellipse([x - r, y - r, x + r, y + r], fill=rgb("#c2187a"))
    # the gum chip (a little circuit stick)
    d.rounded_rectangle([6 * S, 20 * S, 44 * S, 30 * S], radius=2 * S, fill=rgb("#3ff0e0"))
    for k in range(5):
        x = 10 * S + k * 7 * S
        d.rectangle([x, 22 * S, x + 3 * S, 28 * S], fill=rgb("#0b5d63"))
        d.rectangle([x + S, 30 * S, x + 2 * S, 33 * S], fill=rgb("#ffe14a"))
    d.text((AW * S // 2, 6 * S), "NEURO", font=font(LAT, 9 * S), fill=rgb("#ffffff"), anchor="mt")
    d.text((AW * S // 2, 34 * S), "GUM™", font=font(LAT, 7 * S), fill=rgb("#ffe14a"), anchor="mt")
    d.text((3 * S, 1 * S), "ガム", font=font(JP, 4 * S), fill=rgb("#9fe8ff"))
    strip(d)
    frame(d, "#3ff0e0")
    return glow(im, 2 * S, 0.35)


def bolt():
    im = Image.new("RGB", (7 * S, 11 * S), rgb("#07050f"))
    d = ImageDraw.Draw(im)
    d.polygon([(4.5 * S, 0), (0.5 * S, 6 * S), (3.2 * S, 6 * S), (2 * S, 11 * S),
               (6.5 * S, 4.6 * S), (3.8 * S, 4.6 * S), (5.6 * S, 0)], fill=rgb("#ffe14a"))
    return glow(im, S, 0.5)


def main():
    os.makedirs(OUT, exist_ok=True)
    ad_cola().resize((AW, AH), Image.LANCZOS).save(os.path.join(OUT, "ad_0.png"))
    ad_gum().resize((AW, AH), Image.LANCZOS).save(os.path.join(OUT, "ad_1.png"))
    bolt().resize((7, 11), Image.LANCZOS).save(os.path.join(OUT, "bolt.png"))
    big = Image.new("RGB", (AW * 2 * 4 + 40, AH * 4), (20, 20, 20))
    big.paste(Image.open(os.path.join(OUT, "ad_0.png")).resize((AW * 4, AH * 4), Image.NEAREST), (0, 0))
    big.paste(Image.open(os.path.join(OUT, "ad_1.png")).resize((AW * 4, AH * 4), Image.NEAREST), (AW * 4 + 40, 0))
    big.save(os.path.join(OUT, "ads_preview.png"))


if __name__ == "__main__":
    main()
