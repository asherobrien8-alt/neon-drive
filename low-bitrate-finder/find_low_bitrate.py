#!/usr/bin/env python3
"""Find songs below 192 kbps so you know what to re-get as FLAC.

Scans a folder (your music folder, or the Echo Mini / SD card), and writes
LowBitrate-Report.html (grouped by album, worst first) and a .csv next to it.
It also flags formats ReChord can't play yet (anything but FLAC/MP3/WAV).

    pip install mutagen
    python find_low_bitrate.py "D:\\Music"          (or drag a folder onto it)

Nothing is modified, moved or deleted — it only reads tags.
"""
import csv, html, os, sys, time

try:
    import mutagen
except ImportError:
    sys.exit("Needs mutagen:  pip install mutagen")

THRESHOLD = 192  # kbps
AUDIO = {".mp3", ".m4a", ".aac", ".mp4", ".ogg", ".opus", ".wma", ".flac",
         ".wav", ".ape", ".aiff", ".aif", ".dsf", ".dff", ".alac", ".wv"}
LOSSLESS = {".flac", ".wav", ".ape", ".aiff", ".aif", ".dsf", ".dff", ".wv"}
RECHORD_PLAYS = {".flac", ".mp3", ".wav"}


def first(tags, *keys):
    if not tags:
        return ""
    for k in keys:
        try:
            v = tags.get(k)
        except Exception:
            v = None
        if not v:
            continue
        if hasattr(v, "text"):          # ID3 frame
            v = v.text
        if isinstance(v, (list, tuple)):
            v = v[0] if v else ""
        v = str(v).strip()
        if v:
            return v
    return ""


def probe(path):
    ext = os.path.splitext(path)[1].lower()
    info = {"path": path, "ext": ext.lstrip(".").upper(), "kbps": None,
            "artist": "", "album": "", "title": "", "lossless": ext in LOSSLESS,
            "rechord_ok": ext in RECHORD_PLAYS}
    try:
        f = mutagen.File(path)
    except Exception:
        f = None
    if f is not None and f.info is not None:
        br = getattr(f.info, "bitrate", 0) or 0
        if not br and getattr(f.info, "length", 0):
            br = os.path.getsize(path) * 8 / f.info.length
        info["kbps"] = int(round(br / 1000)) if br else None
        codec = (getattr(f.info, "codec", "") or "").lower()
        if ext in (".m4a", ".mp4") and ("alac" in codec or (info["kbps"] or 0) > 600):
            info["lossless"] = True
        t = f.tags
        info["artist"] = first(t, "artist", "TPE1", "\xa9ART", "ARTIST", "Author")
        info["album"] = first(t, "album", "TALB", "\xa9alb", "ALBUM", "WM/AlbumTitle")
        info["title"] = first(t, "title", "TIT2", "\xa9nam", "TITLE", "Title")
    if not info["title"]:
        info["title"] = os.path.splitext(os.path.basename(path))[0]
    return info


def scan(root):
    for d, _, files in os.walk(root):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in AUDIO and not fn.startswith("._"):
                yield probe(os.path.join(d, fn))


def report(root, rows, out_dir):
    low = [r for r in rows if not r["lossless"] and r["kbps"] is not None
           and r["kbps"] < THRESHOLD]
    unknown = [r for r in rows if r["kbps"] is None and not r["lossless"]]
    noplay = [r for r in rows if not r["rechord_ok"]]
    low.sort(key=lambda r: (r["artist"].lower(), r["album"].lower(), r["kbps"]))

    stamp = time.strftime("%Y-%m-%d %H:%M")
    csv_path = os.path.join(out_dir, "LowBitrate-Report.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["kbps", "format", "artist", "album", "title", "path"])
        for r in low:
            w.writerow([r["kbps"], r["ext"], r["artist"], r["album"], r["title"], r["path"]])

    groups = {}
    for r in low:
        groups.setdefault((r["artist"] or "Unknown artist", r["album"] or "Unknown album"), []).append(r)
    order = sorted(groups.items(), key=lambda kv: min(x["kbps"] for x in kv[1]))

    e = html.escape
    parts = ["""<!doctype html><meta charset="utf-8"><title>Low bitrate report</title>
<style>
body{background:#110d1f;color:#eef4ff;font:15px/1.45 Consolas,Menlo,monospace;margin:0;padding:24px}
h1{color:#ff3fbf;font-size:26px;margin:0 0 4px}.sub{color:#8a86b0;margin-bottom:20px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 22px}
.stat{background:#1d1833;border-left:3px solid #3ff0e0;padding:10px 14px}
.stat b{display:block;font-size:22px;color:#3ff0e0}
details{background:#1d1833;margin:0 0 8px;border-left:3px solid #ff3b4f}
summary{cursor:pointer;padding:10px 14px}summary .k{color:#b6ff5a;float:right}
table{width:100%;border-collapse:collapse}td{padding:4px 14px;border-top:1px solid #2a2448}
td.k{color:#ff3b4f;width:70px}.p{color:#8a86b0;font-size:12px;word-break:break-all}
h2{color:#3ff0e0;font-size:17px;margin:26px 0 8px}
</style>""",
        "<h1>LOW BITRATE // REPORT</h1><div class=sub>%s &middot; scanned %s &middot; under %d kbps</div>"
        % (e(stamp), e(root), THRESHOLD),
        "<div class=stats><div class=stat><b>%d</b>songs scanned</div>"
        "<div class=stat><b>%d</b>under %d kbps</div><div class=stat><b>%d</b>albums to upgrade</div>"
        "<div class=stat><b>%d</b>won't play on ReChord</div></div>"
        % (len(rows), len(low), THRESHOLD, len(groups), len(noplay))]
    if not low:
        parts.append("<p>Nothing under %d kbps. Clean library.</p>" % THRESHOLD)
    for (artist, album), items in order:
        parts.append("<details open><summary><b>%s</b> &mdash; %s <span class=k>%d song%s, worst %d kbps</span></summary><table>"
                     % (e(artist), e(album), len(items), "" if len(items) == 1 else "s",
                        min(x["kbps"] for x in items)))
        for r in items:
            parts.append("<tr><td class=k>%d</td><td>%s<div class=p>%s</div></td><td>%s</td></tr>"
                         % (r["kbps"], e(r["title"]), e(r["path"]), e(r["ext"])))
        parts.append("</table></details>")
    if noplay:
        parts.append("<h2>Formats ReChord can't play yet (%d)</h2><p class=sub>ReChord plays FLAC, MP3 and WAV. Convert these or keep stock firmware for them.</p><table>" % len(noplay))
        for r in sorted(noplay, key=lambda r: r["path"].lower())[:500]:
            parts.append("<tr><td class=k>%s</td><td>%s<div class=p>%s</div></td></tr>"
                         % (e(r["ext"]), e(r["title"]), e(r["path"])))
        parts.append("</table>")
    if unknown:
        parts.append("<h2>Couldn't read bitrate (%d)</h2><table>" % len(unknown))
        for r in unknown[:200]:
            parts.append("<tr><td class=p>%s</td></tr>" % e(r["path"]))
        parts.append("</table>")
    html_path = os.path.join(out_dir, "LowBitrate-Report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return html_path, csv_path, len(low), len(rows)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else input("Music folder: ").strip().strip('"')
    if not os.path.isdir(root):
        sys.exit("Not a folder: %s" % root)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(out):
        out = os.getcwd()
    rows = list(scan(root))
    h, c, n, total = report(root, rows, out)
    print("%d of %d songs are under %d kbps" % (n, total, THRESHOLD))
    print("Report: %s\nCSV:    %s" % (h, c))
    if os.name == "nt":
        os.startfile(h)


if __name__ == "__main__":
    main()
