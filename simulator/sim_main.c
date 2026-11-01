/*
 * sim_main.c — Echo Mini simulator core (WebAssembly).
 *
 * Runs ReChord's REAL UI: screen stack, every screen, the theme engine and the
 * media index/query code, exactly as compiled for the device. Only the
 * hardware is replaced: the panel is a RAM framebuffer the page draws, keys
 * come from on-screen buttons, audio is sim_player.c, storage is an
 * in-memory filesystem. The loop below mirrors startup/ap_ui.c.
 */
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <sys/stat.h>

#include "ui/ui.h"
#include "ui/screens/screens.h"
#include "ui/screens/skin_screen.h"
#include "ui/screens/theme_ui.h"
#include "theme/theme.h"
#include "theme/theme_pkg.h"
#include "theme/theme_runtime.h"
#include "theme/theme_skin.h"
#include "drivers/display.h"
#include "services/fs.h"
#include "services/fs_host.h"
#include "services/media_db.h"
#include "services/media_query.h"
#include "services/rechord_files.h"
#include "services/scratch.h"
#include "player/player.h"
#include "services/library_extras.h"
#include "startup/neon_fx.h"

#define EXPORT(n) __attribute__((export_name(n)))

#include "drivers/panel_io_sim.h"
static uint16_t s_fb[DISPLAY_H * DISPLAY_W];
void sim_player_advance(unsigned dt_ms);

/* ---------------------------------------------------------------- stubs */
void log_printf(const char *fmt, ...) { (void)fmt; }
int  input_poll(input_event_t *ev) { (void)ev; return 0; }
int battery_percent(void) { return 75; }

/* ---------------------------------------------------------------- library */
typedef struct { const char *artist, *album, *genre; int year; const char *titles; } album_t;
static const album_t k_lib[] = {
 {"Kavinsky","OutRun","Synthwave",2013,"Prelude|Blizzard|ProtoVision|Odd Look|Rampage|Roadgame|Nightcall|Testarossa Autodrive|Suburbia|Dead Cruiser"},
 {"The Midnight","Endless Summer","Synthwave",2016,"Endless Summer|Sunset|Gloria|Days of Thunder|Jason|The Years|Vampires|Crystalline|Lost Boy"},
 {"The Midnight","Monsters","Synthwave",2020,"Monsters|Dance With Somebody|America 2|Night Skies|Prom Queen|Fire in the Sky"},
 {"Timecop1983","Night Drive","Synthwave",2018,"On the Run|Static|Blue Night|Let Go|Back to You|Faded Lights|Neon Feelings"},
 {"FM-84","Atlas","Synthwave",2016,"Running in the Night|Never Stop|Bend & Break|Wild Ones|Goodbye|Don't Want to Change Your Mind|Atlas"},
 {"Gunship","Gunship","Synthwave",2015,"Tech Noir|Fly for Your Life|Revel in Your Time|Dark All Day|Black Sun on the Horizon|Maximum Overdrive"},
 {"Perturbator","Dangerous Days","Darksynth",2014,"Welcome Back|Satanic Rites|Sentient|She Moves Like a Knife|Future Club|Complete Domination|Hard Wired"},
 {"Carpenter Brut","Trilogy","Darksynth",2015,"Roller Mobster|Turbo Killer|Le Perv|Escape From Midwich Valley|Meet Matt Stryker|Hang 'Em All"},
 {"M83","Hurry Up, We're Dreaming","Electronic",2011,"Intro|Midnight City|Reunion|Wait|Raconte-moi une histoire|Steve McQueen|Splendor"},
 {"Lazerhawk","Redline","Outrun",2013,"Overdrive|Redline|King of the Streets|Electric Groove|So Far Away|Dreamer"},
 {"Mitch Murder","Interceptor","Outrun",2012,"Interceptor|Palmtree Panic|Hollywood Heights|Terminal Velocity|Strike Force"},
 {"Waveshaper","Station Nova","Synthwave",2017,"Station Nova|Hyperspace|Crimson Skies|Orbital|Frontier"},
 {"Daft Punk","Discovery","Electronic",2001,"One More Time|Aerodynamic|Digital Love|Harder, Better, Faster, Stronger|Something About Us|Voyager|Veridis Quo"},
 {"Daft Punk","TRON: Legacy","Soundtrack",2010,"Derezzed|The Grid|Armory|End of Line|Solar Sailer|The Game Has Changed"},
 {"Com Truise","Galactic Melt","Synthfunk",2011,"Terminal|Brokendate|Glawio|Cathode Girls|Air Cal|VHS Sex"},
 {"Dance With the Dead","Loved to Death","Darksynth",2018,"Go|Riot|Salem|Odyssey|Driven Away|Esper"},
 {"Midnight Katana","Neon Ronin","Synthwave",2024,"Neon Ronin|Steel Rain|Shogun Drive|Last Train to Shibuya"},
 {"Neon Tokyo","Afterglow","Synthwave",2023,"Midnight Drive|Shinjuku Lights|Arcade Heart|Rain on Chrome"},
 {"Chrome Samurai","Blade Code","Darksynth",2022,"Mid-Air Blade|Ghost Protocol|Katana Circuit|Overclock"},
 {"Ollie Wride","Thanks for Listening","Synthpop",2020,"Overcome|Back Seat Lover|Never Be Alone|Shadows"},
};
#define LIB_N ((int)(sizeof k_lib / sizeof k_lib[0]))

static void mkdir_p(const char *path)
{
    char tmp[300], *p;

    snprintf(tmp, sizeof tmp, "%s", path);
    for (p = tmp + 1; *p; p++)
        if (*p == '/') { *p = 0; mkdir(tmp, 0777); *p = '/'; }
    mkdir(tmp, 0777);
}

static void clean_name(char *dst, size_t cap, const char *src)
{
    size_t i, j = 0;
    for (i = 0; src[i] && j + 1 < cap; i++)
        dst[j++] = (src[i] == '/' || src[i] == ':' || src[i] == '?') ? '-' : src[i];
    dst[j] = 0;
}

static int build_library(void)
{
    static uint8_t buf[SCRATCH_BYTES];
    int a, n = 0;

    mkdir_p("./Internal/.rechord");
    mkdir_p("./Internal/Music");
    if (media_db_begin(buf, (uint32_t)sizeof buf) != FS_OK)
        return -1;
    for (a = 0; a < LIB_N; a++) {
        const album_t *al = &k_lib[a];
        char t[64], ar[48], ab[48], dir[300];
        const char *p = al->titles;
        int track = 1;

        clean_name(ar, sizeof ar, al->artist);
        clean_name(ab, sizeof ab, al->album);
        snprintf(dir, sizeof dir, "./Internal/Music/%s/%s", ar, ab);
        mkdir_p(dir);
        while (*p) {
            const char *e = strchr(p, '|');
            size_t len = e ? (size_t)(e - p) : strlen(p);
            media_rec_t r;
            char fn[300], file[64];
            FILE *f;

            if (len >= sizeof t) len = sizeof t - 1;
            memcpy(t, p, len); t[len] = 0;
            clean_name(file, sizeof file, t);
            memset(&r, 0, sizeof r);
            snprintf(r.path, sizeof r.path, "Internal/Music/%s/%s/%02d %s.%s", ar, ab,
                     track, file, (a % 4 == 3) ? "mp3" : "flac");
            snprintf(r.title, sizeof r.title, "%s", t);
            snprintf(r.artist, sizeof r.artist, "%s", al->artist);
            snprintf(r.album, sizeof r.album, "%s", al->album);
            snprintf(r.album_artist, sizeof r.album_artist, "%s", al->artist);
            snprintf(r.composer, sizeof r.composer, "Undefined");
            snprintf(r.genre, sizeof r.genre, "%s", al->genre);
            snprintf(r.label, sizeof r.label, "Undefined");
            r.track_no = (uint16_t)track;
            r.year = (uint16_t)al->year;
            r.duration_ms = 150000u + (uint32_t)((a * 37 + track * 53) % 140) * 1000u;
            (void)media_db_add(&r);
            snprintf(fn, sizeof fn, "./%s", r.path);
            if ((f = fopen(fn, "wb")) != 0) fclose(f);
            n++; track++;
            p = e ? e + 1 : p + len;
        }
    }
    return media_db_end() == FS_OK ? n : -1;
}

/* ---------------------------------------------------------------- wiring (ap_ui.c) */
static int media_resolve(uint16_t idx, char *path, int cap)
{
    media_rec_t rec;

    if (!media_db_is_open() && media_db_open() != FS_OK) return -1;
    if (media_db_get((uint32_t)idx, &rec) != FS_OK) return -1;
    if ((int)strlen(rec.path) + 2 > cap) return -1;
    path[0] = '/';
    strcpy(path + 1, rec.path);
    return 0;
}

static void open_library(void)  { ui_push_screen(&library_screen); }
static void open_player(void)   { ui_push_screen(&player_screen); }
static void open_settings(void) { settings_screen_reload(); ui_push_screen(&settings_screen); }
static void open_files(void)
{
    if (browser_screen_state()->path[0] == '\0')
        browser_screen_set_root("/");
    else
        browser_screen_set_root_keep_path("/");
    ui_push_screen(&browser_screen);
}

/* the device's System screen needs hardware: show the classic menu there */
static void open_system(void) { ui_pop_screen(); }

static const char *dev_only(void) { return "device"; }

/* same rows as the device root menu (USB storage / System need hardware) */
static const menu_item_t k_root_items[] = {
    { "Now Playing", NULL, open_player },
    { "Library",     NULL, open_library },
    { "Files",       NULL, open_files },
    { "USB storage", dev_only, NULL },
    { "Settings",    NULL, open_settings },
    { "System",      dev_only, NULL },
};
static const menu_model_t k_root = { "ReChord m9i", k_root_items,
                                     (int)(sizeof k_root_items / sizeof k_root_items[0]), NULL };

static void home_stack_sync(void)
{
    int want = (theme_layout()->home == THEME_HOME_SKIN);
    int i, found = -1;

    for (i = 0; i < ui_stack_depth(); i++)
        if (ui_stack_at(i) == &skin_home_screen) { found = i; break; }
    if (want && found < 0 && ui_stack_depth() >= 1)
        (void)ui_insert_screen(1, &skin_home_screen);
    else if (!want && found >= 0)
        (void)ui_remove_screen(found);
    ui_invalidate_all();
}

static void player_state_changed(int ev, void *user)
{
    (void)user;
    if (ev == PLAYER_EV_STATE || ev == PLAYER_EV_TRACK)
        player_screen_sync_state();
}

static void vol_nav_apply(input_event_t *ev)
{
    const ui_screen_t *top = ui_top_screen();
    int swapped = settings_screen_get()->vol_orient == VOL_ORIENT_SWAPPED;

    if (ev->type != KEY_UP && ev->type != KEY_DOWN) return;
    if (top == 0 || top == &player_screen) return;
    if (top->theme_keys && theme_ui_active()) {
        ev->type = theme_ui_vol_key(ev->type, swapped);
        return;
    }
    if (swapped) ev->type = (ev->type == KEY_UP) ? KEY_DOWN : KEY_UP;
}

static unsigned s_now, s_face_ms, s_theme_ms, s_player_ms, s_last;
static int s_screen_off, s_volume_seen;
/* Neon Drive boot / power-off animations: 0 none, 1 boot, 2 off anim, 3 off */
static int s_fx;
static unsigned s_fx_t0;

static void fx_boot(void)
{
    s_fx = neon_boot_begin() == 0 ? 1 : 0;
    s_fx_t0 = s_now ? s_now : 1;   /* 1: start on the first tick */
    if (!s_fx) ui_invalidate_all();
}

EXPORT("sim_init") int sim_init(void)
{
    int n;

    fs_host_set_root(".");
    panel_io_sim_reset();
    display_init();
    n = build_library();
    player_init();
    extras_init();
    player_set_resolver(media_resolve);
    ui_init();
    player_set_callback(player_state_changed, 0);
    settings_screen_reload();
    {
        const char *id = settings_screen_get()->theme;
        int applied = id[0] && theme_pkg_apply(RECHORD_THEMES_DIR, id) == 0;
        if (!applied)
            (void)theme_pkg_boot(RECHORD_THEMES_DIR, RECHORD_ACTIVE_THEME, "mono");
    }
    player_set_volume(settings_screen_get()->volume_db);
    player_set_shuffle(settings_screen_get()->shuffle);
    player_set_repeat(settings_screen_get()->repeat_mode);
    player_screen_set_volume(player_get_volume());
    s_volume_seen = player_get_volume();
    menu_screen_bind(&k_root);
    ui_push_screen(&menu_screen);
    skin_home_set_actions(open_library, open_player, open_settings);
    skin_home_set_more(open_files, open_system);
    settings_screen_set_theme_applied(home_stack_sync);
    home_stack_sync();
    ui_render();
    fx_boot();
    return n;
}

/* type: KEY_UP/DOWN/SELECT/BACK/MENU/POWER; kind: INPUT_*; lp: long_press */
EXPORT("sim_key") void sim_key(int type, int kind, int lp)
{
    input_event_t ev;

    memset(&ev, 0, sizeof ev);
    ev.type = (input_key_t)type;
    ev.kind = kind;
    ev.long_press = lp;
    ev.now_ms = s_now;
    if (s_fx == 1 || s_fx == 2) return;          /* animations own the screen */
    if (s_fx == 3) {                              /* "off": power boots again */
        if (type == KEY_POWER && kind == INPUT_RELEASE) fx_boot();
        return;
    }
    if (type == KEY_POWER) {
        if (kind == INPUT_LONG) {                 /* hold: virus wipe, then off */
            s_screen_off = 0;
            if (player_get_state() == PLAYER_PLAYING) (void)player_pause();
            neon_off_begin();
            s_fx = 2;
            s_fx_t0 = s_now;
            return;
        }
        if (kind == INPUT_RELEASE && !lp) {
            s_screen_off = !s_screen_off;
            if (!s_screen_off) ui_invalidate_all();
        }
        return;
    }
    if (type == KEY_MENU) {
        if (kind != INPUT_PRESS) return;
        if (s_screen_off) { s_screen_off = 0; ui_invalidate_all(); }
        if (ui_top_screen() == &quick_playlist_screen || ui_top_screen() == &quick_screen)
            ui_pop_screen();
        else
            (void)ui_push_screen(&quick_screen);
        return;
    }
    if (s_screen_off && type == KEY_BACK) return;
    vol_nav_apply(&ev);
    theme_ui_note_input();
    ui_handle_event(&ev);
    if (ui_stack_depth() == 0) {
        ui_push_screen(&menu_screen);
        home_stack_sync();
    }
}

EXPORT("sim_tick") void sim_tick(unsigned now)
{
    s_now = now;
    if (s_last) sim_player_advance(now - s_last);
    s_last = now;
    if (player_get_volume() != s_volume_seen) {
        s_volume_seen = player_get_volume();
        settings_screen_volume_changed(s_volume_seen, now);
    }
    settings_screen_flush_pending(now);
    if (s_fx == 1) {
        if (s_fx_t0 == 1) s_fx_t0 = now;
        if (neon_boot_frame(now - s_fx_t0)) { s_fx = 0; ui_invalidate_all(); ui_render(); }
        return;
    }
    if (s_fx == 2) {
        if (neon_off_frame(now - s_fx_t0)) s_fx = 3;
        return;
    }
    if (s_fx == 3 || s_screen_off) return;

    skin_home_tick(now);
    theme_ui_tick(now);
    if (theme_layout()->home == THEME_HOME_SKIN && ui_top_screen() == &skin_home_screen &&
        theme_skin_animated() && now - s_face_ms >= (unsigned)theme_skin_refresh_ms()) {
        s_face_ms = now;
        if (!skin_home_animate()) {
            int h = theme_skin_refresh_h();
            if (h <= 0) h = theme_layout()->face_h;
            if (h <= 0 || h > DISPLAY_H) h = DISPLAY_H;
            ui_invalidate(0, 0, DISPLAY_W - 1, h - 1);
        }
    }
    if (theme_ui_active() && ui_top_screen() != &skin_home_screen && theme_skin_animated() &&
        now - s_theme_ms >= (unsigned)theme_skin_refresh_ms()) {
        s_theme_ms = now;
        if (!(ui_top_screen() == &player_screen && player_screen_animate())) {
            int h = theme_skin_refresh_h();
            if (h <= 0) h = theme_layout()->face_h;
            if (h <= 0 || h > DISPLAY_H) h = DISPLAY_H;
            ui_invalidate(0, 0, DISPLAY_W - 1, h - 1);
        }
    }
    if (ui_top_screen() == &player_screen && now - s_player_ms >= 100u) {
        s_player_ms = now;
        player_screen_refresh();
    }
    ui_render();
}

/* what the PANEL shows (only flushed pixels), like the real screen */
EXPORT("sim_fb") uint16_t *sim_fb(void)
{
    int x, y;
    for (y = 0; y < DISPLAY_H; y++)
        for (x = 0; x < DISPLAY_W; x++)
            s_fb[y * DISPLAY_W + x] = s_screen_off ? 0 : panel_io_sim_pixel(x, y);
    return s_fb;
}
EXPORT("sim_screen_off") int sim_screen_off(void) { return s_screen_off || s_fx == 3; }
EXPORT("sim_top") const char *sim_top(void)
{
    const ui_screen_t *t = ui_top_screen();
    return t && t->name ? t->name : "";
}

/* WASI reactor needs no main; native test builds use this one */
#ifndef SIM_WASM
#include <stdlib.h>
int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    return sim_init() > 0 ? 0 : 1;
}
#endif
