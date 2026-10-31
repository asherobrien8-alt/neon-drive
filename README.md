# NEON DRIVE — retrowave theme for the Snowsky Echo Mini

A full retrowave / cyberpunk makeover for the FiiO Snowsky **Echo Mini**:

- **Live wallpaper home screen.** An 80s wedge car cruises a neon road into a striped sunset, with pink palms and a scrolling grid.
- **Volume runner.** On Now Playing, a glowing runner stands on the volume track. Turn it up and he sprints right; turn it down and he sprints left.
- **Cyber settings.** Terminal-style `SYS://CONFIG` screen.
- **Cleaner navigation.** A proper library (Artist / Album / Genre / Year / …), a file browser, and a counter showing where you are in every list.
- **Low-bitrate finder.** A PC tool that lists every song under 192 kbps, grouped by album, so you know what to re-get as FLAC.

![all screens](docs/preview/overview.png)

| Home (live) | Volume runner |
|---|---|
| ![home](docs/preview/home_live_wallpaper.gif) | ![runner](docs/preview/now_playing_volume_runner.gif) |

These previews come from the real theme engine running on a PC, so they show exactly what the player draws.

---

## Read this first

Neon Drive runs on **ReChord**, a community-built custom firmware for the Echo Mini (the Echo Mini can't run Rockbox). ReChord is new. It boots and plays on real players, but compared to the stock firmware:

| | Stock FiiO | ReChord + Neon Drive |
|---|---|---|
| FLAC, MP3, WAV | ✅ | ✅ |
| M4A/AAC, OGG, APE, DSD | ✅ | ❌ not yet |
| Bluetooth | ✅ | ❌ not yet |
| USB DAC mode | ✅ | ❌ |
| 96 kHz files | ✅ | ✅ (rare crackle) |
| Copy music over USB | ✅ | ✅ internal storage (SD card is read-only over USB; use a card reader) |
| Themes / live wallpaper / runner | ❌ | ✅ |

**You can always go back.** Copy FiiO's official firmware file onto the player the same way and it returns to stock.

---

## Install (about 10 minutes)

**Before you start**

1. Back up any music on the player's internal storage (updates can wipe it).
2. Download the **official FiiO firmware** for your Echo Mini and keep it. That's your undo button: <https://fiio.com/newsinfo/1144405.html>
3. Take the **microSD card out**.
4. Charge the player above 50%.

**Step 1: firmware**

1. Plug the Echo Mini into your PC. It shows up as a drive.
2. Copy `STEP-1-FIRMWARE/HIFIEC90.IMG` to the **top level** of the player's drive (not inside a folder).
3. Eject the drive in Windows, unplug, and restart the player. It installs by itself; wait for it to boot.

**Step 2: theme**

1. Plug it back in. It shows up as a drive again (screen says *USB mass storage*).
2. Open `STEP-2-THEME`, copy the **`.rechord`** folder onto the top level of the player's drive, and click **Replace** if Windows asks.
3. Eject, unplug. Neon Drive loads on the next boot.

**Step 3: first boot**

1. On the home screen pick **MENU → System → Rebuild index** so the library finds your songs (do this again whenever you add music).
2. Put the microSD card back.

### Controls

| | |
|---|---|
| VOL + / − | move through menus · change volume on Now Playing |
| PLAY | open / select |
| BACK | go back |
| MENU (home bar) | full menu: Files, USB storage, System |
| Power, short press | screen off / on |

### Going back to stock

Copy the official FiiO `HIFIECxx.IMG` to the top level of the player, eject, restart. If the player ever won't boot at all, ReChord's recovery guide is here: <https://github.com/brnomt/FiioDcomp/blob/master/docs/FLASHING.md#recovery-if-something-goes-wrong>

---

## Low-bitrate finder

In `low-bitrate-finder/`:

- **Windows (nothing to install):** double-click **`Find Low Bitrate Songs.bat`** and pick your music folder, or drag the folder onto the .bat file.
- **Any OS:** `pip install mutagen`, then `python find_low_bitrate.py "path/to/music"`.

It writes `LowBitrate-Report.html` and a `.csv` to your Desktop: every song under 192 kbps, grouped by album with the worst first. It also lists files ReChord can't play yet (M4A/OGG and so on). It only reads files and never changes, moves or deletes anything.

---

## For tinkerers

```
src/                 theme sources (readable colours + comments)
tools/build_theme.py compiles src/ -> STEP-2-THEME/ and checks every ReChord limit
tools/make_assets.py the pixel-art sprites (car, palm, runner) -> 1-bit assets
tools/previews.sh    re-renders docs/preview with the real engine
firmware/build.sh    rebuilds HIFIEC90.IMG: ReChord @ pinned commit + neon-drive-engine.patch
```

The engine patch adds a few theme features to ReChord: 2×/3× text, transparent text and sprites, mirrored sprites, colourable list selection bars, and a `menu` home button. Packages that don't use them render exactly as before, and ReChord's own test suites pass with the patch applied.

All art is original. ReChord is by [brnomt](https://github.com/brnomt/FiioDcomp). This project isn't affiliated with FiiO or Snowsky.
