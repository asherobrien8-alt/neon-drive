/*
 * render_skin.c — host renderer for ReChord theme packages.
 *
 * Runs the REAL theme engine (theme_pkg + theme_skin) against the REAL
 * display driver wired to the simulated panel, then dumps a PPM. What you
 * see is what the Echo Mini draws (same 8x8 font, same RGB565 maths).
 *
 * usage: render_skin <themes_root> <theme_id> <skin_file> <out.ppm>
 *                    [t_ms] [sel] [list:none|library|settings|browser|cat]
 *                    [volume_db] [prev_frames]
 *
 * prev_frames: render the skin this many times at earlier t (16ms apart,
 * with volume ramping from volume_db+/-3) before the final frame, so
 * "previous frame" variables (direction detection) settle like on device.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "drivers/display.h"
#include "drivers/panel_io_sim.h"
#include "theme/theme.h"
#include "theme/theme_runtime.h"
#include "theme/theme_skin.h"

static const char *lib_rows[] = { "All Songs", "Album", "Artist", "Genre",
    "Year", "Label", "Album Artist", "Composer" };
static const char *set_rows[] = { "Volume", "Shuffle", "Repeat", "Resume",
    "Fade", "Auto-off", "ReplayGain", "Equalizer", "Brightness", "Theme",
    "Controls" };
static const char *set_vals[] = { "-14 dB", "Off", "All", "Track", "300 ms",
    "30 min", "Album", "Neon", "4", "Neon Drive", "Normal" };
static const char *br_rows[] = { "..", "Daft Punk", "Kavinsky", "M83",
    "Perturbator", "The Midnight", "Timecop1983", "FM-84", "Gunship",
    "Carpenter Brut", "Lazerhawk", "Mitch Murder" };
static const char *cat_rows[] = { "Nightcall", "Odd Look", "Roadgame",
    "ProtoVision", "Blizzard", "Testarossa Autodrive", "Pacific Coast Hwy",
    "Rampage", "Zombie Shark", "Dead Cities" };
static const char *cat_vals[] = { "4:18", "4:11", "3:52", "4:05", "4:44",
    "3:39", "4:57", "3:31", "4:20", "5:02" };

static const char **g_rows, **g_vals;

static const char *lab(int i, char *b, int c)
{ snprintf(b, (size_t)c, "%s", g_rows[i]); return b; }
static const char *val(int i, char *b, int c)
{ if (!g_vals) return 0; snprintf(b, (size_t)c, "%s", g_vals[i]); return b; }

int main(int argc, char **argv)
{
    theme_skin_state_t st;
    theme_skin_list_source_t src;
    unsigned t;
    int sel, vol, prev, i, rc;
    const char *list;

    if (argc < 5) {
        fprintf(stderr, "usage: %s root id skin out.ppm [t] [sel] [list] [vol] [prev]\n", argv[0]);
        return 2;
    }
    t = argc > 5 ? (unsigned)atoi(argv[5]) : 0;
    sel = argc > 6 ? atoi(argv[6]) : 0;
    list = argc > 7 ? argv[7] : "none";
    vol = argc > 8 ? atoi(argv[8]) : -14;
    prev = argc > 9 ? atoi(argv[9]) : 0;

    panel_io_sim_reset();
    display_init();

    rc = theme_pkg_apply(argv[1], argv[2]);
    if (rc != 0) { fprintf(stderr, "theme_pkg_apply failed %d\n", rc); return 1; }
    rc = theme_skin_load(argv[1], argv[2], argv[3]);
    if (rc != 0) { fprintf(stderr, "theme_skin_load failed %d\n", rc); return 1; }

    memset(&src, 0, sizeof src);
    g_vals = 0;
    if (!strcmp(list, "library")) { g_rows = lib_rows; g_vals = 0; src.count = 8; }
    else if (!strcmp(list, "settings")) { g_rows = set_rows; g_vals = set_vals; src.count = 11; }
    else if (!strcmp(list, "browser")) { g_rows = br_rows; src.count = 12; }
    else if (!strcmp(list, "cat")) { g_rows = cat_rows; g_vals = cat_vals; src.count = 10; }
    if (src.count) {
        src.label = lab;
        src.value = g_vals ? val : 0;
        theme_skin_set_list(&src);
    }

    memset(&st, 0, sizeof st);
    st.playing = 1; st.state = "Playing";
    st.volume_db = vol; st.battery_pct = 75;
    st.title = "Nightcall"; st.artist = "Kavinsky"; st.album = "OutRun";
    st.path = "/Internal/Music/Kavinsky/OutRun/01 Nightcall.flac";
    st.heading = !strcmp(list, "settings") ? "Settings" :
                 !strcmp(list, "browser") ? "/Internal/Music" :
                 !strcmp(list, "cat") ? "Songs" : "Library";
    st.position_ms = 94000; st.duration_ms = 258000;
    st.bits = 24; st.sample_rate = 96000;
    st.playlist_pos = 3; st.playlist_count = 12; st.repeat = 1;

    if (getenv("SEQ")) {          /* SEQ="v,v,v..." one frame per entry, 60 ms apart */
        char buf[8192], *tok, path[512];
        int k = 0, step = getenv("STEP") ? atoi(getenv("STEP")) : 60;
        snprintf(buf, sizeof buf, "%s", getenv("SEQ"));
        for (tok = strtok(buf, ","); tok; tok = strtok(0, ","), k++) {
            st.volume_db = atoi(tok);
            st.position_ms = 94000 + k * step;
            theme_skin_render(t + (unsigned)(k * step), 10, sel, 0, &st);
            display_flush_rows(0, DISPLAY_H - 1);
            snprintf(path, sizeof path, "%s_%03d.ppm", argv[4], k);
            panel_io_sim_write_ppm(path);
        }
        return 0;
    }
    {
        int top = 0, rows = theme_skin_list_rows();
        if (rows > 0 && sel >= rows) top = sel - rows + 1;
        for (i = prev; i > 0; i--) {
            theme_skin_state_t p = st;
            /* ramp toward the final volume so direction vars settle */
            p.volume_db = (argc > 10 && i > 4) ? atoi(argv[10]) : vol;
            theme_skin_render(t - (unsigned)i * 60u, 10, sel, top, &p);
        }
        theme_skin_render(t, prev ? 10 : 5000, sel, top, &st);
    }
    display_flush_rows(0, DISPLAY_H - 1);
    if (panel_io_sim_write_ppm(argv[4]) != 0) return 1;
    return 0;
}
