# NEON DRIVE — retrowave theme for the Snowsky Echo Mini

A full retrowave / cyberpunk makeover for the FiiO Snowsky **Echo Mini**:

- **Live home screen.** Five slanted neon tags (File Browser, Media Library, Playing, Music Settings, System Settings). The selected one glows red and flickers like a real neon tube. Next to them is a night city with lit windows, blinking antenna lights, twinkling stars and a striped sun that glows, with rings radiating out from it.
- **Volume runner.** On Now Playing, a glowing runner stands on the volume track. Turn it up and he sprints right; turn it down and he sprints left.
- **Cyber settings.** Terminal-style `SYS://CONFIG` screen.
- **Search.** Library → Search: spin letters with VOL, add with PLAY, and matches (title, artist or album) show up live as you type.
- **A-Z jump.** In any long list (Artists, Albums, All Songs, search results), **hold PLAY** for a letter grid and jump straight to that letter.
- **Cleaner navigation.** A proper library (Artist / Album / Genre / Year / …), a file browser, and a counter showing where you are in every list.
- **Low-bitrate finder.** A PC tool that lists every song under 192 kbps, grouped by album, so you know what to re-get as FLAC.

![all screens](docs/preview/overview.png)

| Home (live) | Volume runner |
|---|---|
| ![home](docs/preview/home_live_wallpaper.gif) | ![runner](docs/preview/now_playing_volume_runner.gif) |
| **Search** | **A-Z jump (hold PLAY)** |
| ![search](docs/preview/search.png) | ![a-z](docs/preview/az.png) |

## Try it first: the simulator

Open **`simulator/index.html`** in any browser (phone works too; nothing to install). It runs ReChord's **actual firmware UI code**, compiled to WebAssembly: the same screens, theme engine and library index that run on the player, with a demo library of 122 synthwave tracks. Only the hardware is pretend: the buttons are on screen and there's no audio (songs "play" on a timer).

Buttons work like the real ones: hold PLAY for A-Z, and VOL repeats when held. On a computer you can use <kbd>↑</kbd>/<kbd>↓</kbd>, <kbd>Enter</kbd>, <kbd>Backspace</kbd> and <kbd>M</kbd>.

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

1. On the home screen pick **SYSTEM SETTINGS → Rebuild index** so the library finds your songs (do this again whenever you add music).
2. Put the microSD card back.

### Controls

| | |
|---|---|
| VOL + / − | move up / down through menus · change volume on Now Playing · spin letters in Search |
| PLAY | open / select · add a letter in Search |
| hold PLAY | A-Z jump in lists · show results in Search |
| BACK | go back |
| MENU button | quick settings (shuffle, repeat, playlist) |
| BACK on the home screen | classic menu: Files, USB storage, System |
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
simulator/build.sh   rebuilds simulator/index.html (needs `pip install ziglang==0.13.0`, node)
```

The firmware patch (`firmware/neon-drive-engine.patch`) adds to ReChord:

- **Search** (`search_screen.c`, `mq_search_init`) and **A-Z jump** (`az_screen.c`, `mq_initial_*`), with new host tests in `services/tests/test_search_az.c`.
- **Theme engine extras:** 2×/3× text, transparent text and sprites, mirrored sprites, colourable list selection bars, a `menu` home button, and the real battery level for skins (upstream always passed "unknown").

Themes that don't use the extras render exactly as before, and all of ReChord's test suites (UI, theme, services) pass with the patch. The image adds about 5 KB of code and 112 bytes of RAM, still under ReChord's RAM ceiling.

All art is original. ReChord is by [brnomt](https://github.com/brnomt/FiioDcomp). This project isn't affiliated with FiiO or Snowsky.
