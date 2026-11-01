#!/usr/bin/env python3
"""Neon Drive — procedural neo-Tokyo / Chongqing night city (original art).

Renders at 4x (1280x680) with layered fog, lit towers, kanji neon, a
holographic billboard, a cable-stayed bridge with light trails and a river
with reflections, then bloom, haze and a 4x downsample. Outputs, for the
Echo Mini's 320x170 panel:

  city.png / city.565        the home background (left side kept dark for
                             the menu tags)
  holo_<n>.565               billboard animation frames
  sites.json                 positions/colours of the animated overlays

Deterministic (fixed seed) so rebuilding gives the same picture.
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 4
W, H = 320 * S, 170 * S
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
FONT_JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
rng = random.Random(2077)
np_rng = np.random.default_rng(2077)


def font(px):
    return ImageFont.truetype(FONT_JP, px, index=0)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- layers
def sky():
    y = np.linspace(0, 1, H)[:, None]
    top, mid, hor = np.array(rgb("#05040f")), np.array(rgb("#20104a")), np.array(rgb("#8a2a6e"))
    a = np.clip(y / 0.45, 0, 1)
    b = np.clip((y - 0.40) / 0.32, 0, 1)
    col = top * (1 - a) + mid * a
    col = col * (1 - b) + hor * b
    img = np.repeat(col[:, None, :], W, axis=1).astype(np.float32).reshape(H, W, 3)
    # smog: soft noise clouds, warmer near the horizon
    n = np_rng.random((H // 32 + 2, W // 32 + 2)).astype(np.float32)
    n = np.array(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    band = np.exp(-((np.linspace(0, 1, H) - 0.42) / 0.18) ** 2)[:, None]
    img += (n * band)[:, :, None] * np.array([38, 14, 46], np.float32)
    return img


def add(img, layer, alpha=1.0):
    a = np.asarray(layer, np.float32) / 255.0
    rgbv, al = a[..., :3] * 255.0, a[..., 3:4] * alpha
    img[:] = img * (1 - al) + rgbv * al


def glow_layer(draw_fn, radius, strength):
    """draw on a black RGBA canvas, return (sharp, bloom) float arrays"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay))
    sharp = np.asarray(lay, np.float32)
    rgbl = Image.fromarray(np.uint8(sharp[..., :3] * (sharp[..., 3:4] / 255.0)))
    bloom = np.asarray(rgbl.filter(ImageFilter.GaussianBlur(radius)), np.float32) * strength
    return sharp, bloom


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (255,)


def tower(d, x, w, top, base, col, win_cols, lit_p, win_style, edge=None, seed=0, crown=None):
    r = random.Random(seed)
    lit = shade(col, 1.55)
    # body: dark face + lit side (3D)
    d.rectangle([x, top, x + w, base], fill=col)
    d.rectangle([x, top, x + max(S, w // 5), base], fill=lit)
    crown_top = top
    if w > 30 * S // 2 and r.random() < 0.75:
        cw = int(w * r.uniform(0.45, 0.72))
        cx = x + (w - cw) // 2
        ch = r.randint(8, 22) * S // 2
        d.rectangle([cx, top - ch, cx + cw, top], fill=col)
        d.rectangle([cx, top - ch, cx + max(S, cw // 5), top], fill=lit)
        crown_top = top - ch
        if r.random() < 0.8:
            ax = cx + cw // 2
            d.rectangle([ax - S // 2, crown_top - 16 * S, ax + S // 2, crown_top], fill=lit)
            d.rectangle([ax - S, crown_top - 17 * S, ax + S, crown_top - 15 * S], fill=(255, 40, 60, 255))
    if crown:
        d.rectangle([x, top, x + w, top + S // 2], fill=crown + (255,))
    # windows: small and dense, floors banded
    yy = top + 3 * S
    floor = 0
    while yy < base - 2 * S:
        band_on = r.random() < 0.75
        if win_style == "grid":
            xx = x + 2 * S
            while xx < x + w - 2 * S:
                if band_on and r.random() < lit_p:
                    c = r.choice(win_cols)
                    d.rectangle([xx, yy, xx + S - 1, yy + S + S // 2], fill=c + (255,))
                xx += 2 * S + S // 2
            yy += 3 * S
        else:
            if band_on and r.random() < lit_p + 0.2:
                c = r.choice(win_cols)
                l = x + S + r.randint(0, w // 5)
                rr = x + w - S - r.randint(0, w // 5)
                d.rectangle([l, yy, rr, yy + S - 1], fill=c + (200,))
            yy += 2 * S
        floor += 1
    if edge:
        d.rectangle([x, crown_top, x + S // 2 + 1, base], fill=edge + (255,))


def main():
    os.makedirs(OUT, exist_ok=True)
    img = sky()

    # stars (sparse, upper sky)
    st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(st)
    for _ in range(70):
        x, y = rng.randrange(W // 3, W), rng.randrange(0, int(H * 0.28))
        b = rng.randint(120, 255)
        ds.rectangle([x, y, x + S // 2, y + S // 2], fill=(b, b, 255, 255))
    add(img, st)

    # moon-ish haze disc behind the skyline (soft magenta glow)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([int(W * .62), int(H * .14), int(W * .62) + 120 * S, int(H * .14) + 120 * S],
                                  fill=(255, 60, 140, 70))
    halo = halo.filter(ImageFilter.GaussianBlur(40 * S // 2))
    add(img, halo)

    WIN_WARM = [rgb("#ffd89a"), rgb("#ffe9c4"), rgb("#ffc070")]
    WIN_COOL = [rgb("#8ff0ff"), rgb("#5fd8e8"), rgb("#c8f6ff")]
    WIN_MIX = WIN_WARM + WIN_COOL + [rgb("#ff7ac8")]

    # --- far skyline (fogged, cool)
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(far)
    x = 0
    while x < W:
        w = rng.randint(14, 34) * S
        top = int(H * rng.uniform(0.30, 0.52))
        tower(d, x, w, top, int(H * .80), (48, 34, 92, 255), [rgb("#7a8ad8"), rgb("#9a7ac8")], 0.22, "grid",
              seed=rng.random())
        x += w + rng.randint(0, 4) * S
    # megatower with spire (behind the mid layer)
    mt = ImageDraw.Draw(far)
    mx = 222 * S
    tower(mt, mx, 22 * S, int(H * .10), int(H * .80), (44, 32, 90, 255), [rgb("#9ab0ff"), rgb("#ff9ad8")], 0.3,
          "strip", seed=7, crown=rgb("#ff3fbf"))
    mt.polygon([(mx + 6 * S, int(H * .10)), (mx + 11 * S, int(H * .01)), (mx + 16 * S, int(H * .10))],
               fill=(60, 44, 110, 255))
    mt.rectangle([mx + 10 * S, 0, mx + 12 * S, int(H * .02)], fill=(255, 40, 60, 255))
    add(img, far, 0.88)
    # fog band
    fog = np.exp(-((np.linspace(0, 1, H) - 0.62) / 0.12) ** 2)[:, None, None]
    img += fog * np.array([60, 26, 70], np.float32) * 0.55

    # --- mid skyline
    mid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(mid)
    x = int(W * 0.20)
    while x < W:
        w = rng.randint(20, 44) * S
        top = int(H * rng.uniform(0.18, 0.46))
        tower(d, x, w, top, int(H * .84), (30, 24, 66, 255), WIN_MIX, 0.36,
              rng.choice(["grid", "strip"]), edge=rng.choice([None, rgb("#3ff0e0"), rgb("#ff3fbf")]),
              seed=rng.random())
        x += w + rng.randint(2, 8) * S
    add(img, mid)

    # --- hero towers (near, detailed) + their neon, bloom later
    neon_sharp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dn = ImageDraw.Draw(neon_sharp)
    near = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(near)
    sites = {"signs": [], "holo": None, "twinkle": [], "trail": None}

    heroes = [  # x, w, top (fractions / px@1x)
        (172, 34, 22, "strip", rgb("#3ff0e0")),
        (208, 26, 40, "grid", None),
        (236, 40, 10, "strip", rgb("#ff3fbf")),
        (278, 24, 52, "grid", rgb("#3ff0e0")),
        (300, 22, 30, "strip", None),
    ]
    for i, (hx, hw, ht, style, edge) in enumerate(heroes):
        tower(d, hx * S, hw * S, ht * S, int(H * .88), (20, 16, 42, 255), WIN_MIX, 0.5, style, edge=edge,
              seed=100 + i, crown=rng.choice([rgb("#3ff0e0"), rgb("#ff3fbf"), rgb("#ffd54a"), None]))
        if edge:
            dn.rectangle([hx * S, ht * S, hx * S + S // 2 + 1, int(H * .88)], fill=edge + (255,))
        # twinkle zone: a strip of the facade the firmware animates
        sites["twinkle"].append({"x": hx + 3, "y": ht + 8, "w": hw - 6, "h": 26, "base": None})
    add(img, near)

    # holographic billboard on tower 3 (x 236..276)
    bx, by, bw, bh = 242, 30, 26, 44
    sites["holo"] = {"x": bx, "y": by, "w": bw, "h": bh}
    d2 = ImageDraw.Draw(neon_sharp)
    d2.rectangle([bx * S - S, by * S - S, (bx + bw) * S + S, (by + bh) * S + S], outline=rgb("#ff3fbf") + (255,),
                 width=S // 2 + 1)

    # vertical kanji signs (original words)
    signs = [("電脳", 196, 70, rgb("#ff3b4f")), ("夜市", 228, 86, rgb("#3ff0e0")),
             ("拉麺", 296, 74, rgb("#ffd54a")), ("ネオン", 166, 56, rgb("#ff3fbf"))]
    for txt, sx, sy, col in signs:
        f = font(9 * S)
        hgt = len(txt) * 10 * S + 2 * S
        d2.rectangle([sx * S - S, sy * S - S, sx * S + 11 * S, sy * S + hgt], fill=(10, 6, 20, 255),
                     outline=col + (255,), width=S // 2 + 1)
        for k, ch in enumerate(txt):
            d2.text((sx * S + S // 2, sy * S + k * 10 * S), ch, font=f, fill=col + (255,))
        sites["signs"].append({"x": sx - 1, "y": sy - 1, "w": 13, "h": hgt // S + 2, "color": "#%02x%02x%02x" % col})
    # horizontal sign on the far right tower
    f = font(7 * S)
    d2.rectangle([262 * S, 104 * S, 316 * S, 114 * S], fill=(12, 8, 22, 255), outline=rgb("#ffd54a") + (255,),
                 width=S // 2)
    d2.text((265 * S, 104 * S), "暁 AKATSUKI", font=f, fill=rgb("#ffd54a") + (255,))
    sites["signs"].append({"x": 262, "y": 104, "w": 55, "h": 11, "color": "#ffd54a"})

    # --- bridge with cables + light trails (Chongqing)
    br = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(br)
    deck = int(H * .80)
    db.rectangle([150 * S, deck, W, deck + 3 * S], fill=(20, 16, 40, 255))
    for px in (196, 286):
        db.rectangle([px * S - S, int(H * .48), px * S + S, deck + 3 * S], fill=(30, 26, 56, 255))
        for k in range(1, 9):
            for sgn in (-1, 1):
                ex = px * S + sgn * k * 5 * S
                db.line([(px * S, int(H * .50) + k * 2 * S), (ex, deck)], fill=(120, 120, 170, 200), width=1)
    add(img, br)
    trails = lambda dd: (dd.rectangle([150 * S, deck - S, W, deck - S // 2], fill=(255, 50, 70, 255)),
                         dd.rectangle([150 * S, deck + S, W, deck + S + S // 2], fill=(255, 240, 220, 255)))
    sites["trail"] = {"x": 150, "y": deck // S - 1, "w": 170, "h": 3}

    # --- neon bloom
    trail_sharp, trail_bloom = glow_layer(trails, 3 * S, 1.2)
    neon = np.asarray(neon_sharp, np.float32)
    neon_rgb = Image.fromarray(np.uint8(neon[..., :3] * (neon[..., 3:4] / 255.0)))
    bloom = np.asarray(neon_rgb.filter(ImageFilter.GaussianBlur(4 * S)), np.float32) * 1.6
    bloom += np.asarray(neon_rgb.filter(ImageFilter.GaussianBlur(14 * S)), np.float32) * 0.9
    add(img, neon_sharp)
    img += bloom + trail_bloom
    add(img, Image.fromarray(np.uint8(trail_sharp)))

    # --- river + reflections
    wy = int(H * .84)
    refl = img[wy - (H - wy):wy][::-1].copy()
    refl = np.asarray(Image.fromarray(np.uint8(np.clip(refl, 0, 255))).filter(ImageFilter.GaussianBlur(2 * S)),
                      np.float32)
    rows = np.arange(H - wy)
    shift = (np.sin(rows / (1.3 * S)) * 3 * S).astype(int)
    for r in range(H - wy):
        refl[r] = np.roll(refl[r], shift[r], axis=0)
    water = refl * 0.42 + np.array(rgb("#0a0820"), np.float32) * 0.58
    for r in range(0, H - wy, 3 * S):  # ripple highlights
        water[r:r + 1] *= 1.25
    img[wy:] = water[:H - wy]
    img[wy:wy + S // 2] = np.array(rgb("#3ff0e0"), np.float32) * 0.6

    # --- foreground rooftops (left-centre), with tanks, AC units, cables
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    df = ImageDraw.Draw(fg)
    roofs = [(118, 46, 132), (160, 30, 142), (186, 40, 150), (300, 30, 138)]
    for rx, rw, ry in roofs:
        df.rectangle([rx * S, ry * S, (rx + rw) * S, H], fill=(10, 8, 20, 255))
        df.rectangle([rx * S, ry * S, (rx + rw) * S, ry * S + S // 2], fill=(70, 50, 110, 255))
        for k in range(rng.randint(2, 4)):
            ux = (rx + rng.randint(2, rw - 8)) * S
            kind = rng.random()
            if kind < 0.4:   # water tank on legs
                df.rectangle([ux, (ry - 9) * S, ux + 6 * S, (ry - 4) * S], fill=(16, 12, 30, 255))
                df.line([(ux + S, (ry - 4) * S), (ux + S, ry * S)], fill=(16, 12, 30, 255), width=S // 2)
                df.line([(ux + 5 * S, (ry - 4) * S), (ux + 5 * S, ry * S)], fill=(16, 12, 30, 255), width=S // 2)
            elif kind < 0.8:  # AC units
                df.rectangle([ux, (ry - 3) * S, ux + 4 * S, ry * S], fill=(22, 18, 40, 255))
            else:             # small lit window shack
                df.rectangle([ux, (ry - 6) * S, ux + 7 * S, ry * S], fill=(16, 12, 30, 255))
                df.rectangle([ux + 2 * S, (ry - 4) * S, ux + 4 * S, (ry - 2) * S], fill=(255, 200, 120, 255))
    for k in range(4):  # cables between rooftops
        x0 = rng.randint(118, 200) * S
        x1 = x0 + rng.randint(30, 90) * S
        y0 = rng.randint(118, 136) * S
        pts = [(x0 + (x1 - x0) * t / 20, y0 + math.sin(math.pi * t / 20) * 5 * S) for t in range(21)]
        df.line(pts, fill=(30, 24, 50, 255), width=1)
    add(img, fg)

    # --- light rain + film grain
    rain = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(rain)
    for _ in range(260):
        x, y = rng.randrange(W), rng.randrange(H)
        dr.line([(x, y), (x - 3 * S, y + 9 * S)], fill=(170, 190, 255, 38), width=1)
    add(img, rain)
    img += np_rng.normal(0, 3.0, img.shape).astype(np.float32)

    # --- menu side: darken the left so the tags read; vignette
    xs = np.linspace(0, 1, W)[None, :, None]
    left = np.clip((xs - 0.32) / 0.22, 0, 1)
    img *= (0.22 + 0.78 * left)
    yv = np.linspace(-1, 1, H)[:, None, None]
    img *= 1 - 0.18 * yv ** 2

    big = Image.fromarray(np.uint8(np.clip(img, 0, 255)))
    small = big.resize((320, 170), Image.LANCZOS)
    small.save(os.path.join(OUT, "city.png"))
    big.resize((640, 340), Image.LANCZOS).save(os.path.join(OUT, "city_2x.png"))

    # sample base colours for overlays from the final image
    px = small.load()
    for s in sites["signs"]:
        s["off"] = "#%02x%02x%02x" % tuple(int(v * 0.25) for v in px[s["x"] + 2, s["y"] + 3])
    for t in sites["twinkle"]:
        t["base"] = "#%02x%02x%02x" % px[t["x"] + 1, t["y"] + 1]

    # holographic billboard frames (original abstract motion graphics)
    holo = []
    for fi in range(4):
        fr = Image.new("RGB", (bw * S, bh * S), rgb("#14082a"))
        dh = ImageDraw.Draw(fr)
        for k in range(8):  # scan bars
            yb = ((k * 6 + fi * 3) % bh) * S
            dh.rectangle([0, yb, bw * S, yb + S], fill=(60, 20, 90))
        ph = fi * math.pi / 2
        for k in range(5):  # rotating diamond logo
            r0 = (8 + k * 2) * S
            cx, cy = bw * S // 2, int(bh * S * 0.40)
            pts = [(cx + r0 * math.cos(ph + j * math.pi / 2 + k * .2),
                    cy + r0 * math.sin(ph + j * math.pi / 2 + k * .2) * 0.8) for j in range(4)]
            dh.polygon(pts, outline=(255, 60 + k * 30, 190), width=S // 2 + 1)
        f = font(6 * S)
        dh.text((S * 2, int(bh * S * 0.72)), ["ネオ", "東京", "未来", "電波"][fi], font=f, fill=(140, 250, 255))
        g = fr.filter(ImageFilter.GaussianBlur(S))
        fr = Image.blend(fr, g, 0.35).resize((bw, bh), Image.LANCZOS)
        holo.append(fr)
        fr.save(os.path.join(OUT, "holo_%d.png" % fi))
    json.dump(sites, open(os.path.join(OUT, "sites.json"), "w"), indent=1)
    print("rendered", OUT)


if __name__ == "__main__":
    main()
