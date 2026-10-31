/*
 * sim_player.c — a pretend audio player for the browser simulator.
 *
 * Implements ReChord's player API (firmware/player/player.h) with a clock
 * instead of a decoder: tracks "play" in real time, auto-advance, honour
 * shuffle/repeat, and fire the same PLAYER_EV_* callbacks, so every screen
 * behaves as on the device. Track metadata comes from the real media index.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "player/player.h"
#include "services/media_db.h"
#include "services/fs.h"

#define QMAX 2048

static uint16_t s_q[QMAX];
static int  s_n, s_pos, s_state = PLAYER_STOPPED, s_vol = -18;
static int  s_shuffle, s_repeat, s_rg;
static long s_pos_ms;
static int  s_have;
static track_info_t s_ti;
static player_event_fn s_cb;
static void *s_cb_user;
static int (*s_resolve)(uint16_t, char *, int);
static int  s_qkind; static char s_qval[PLAYER_QUEUE_VALUE_MAX]; static int s_qcat;

static void fire(int ev) { if (s_cb) s_cb(ev, s_cb_user); }

static void fill_from_rec(const media_rec_t *r)
{
    unsigned h = 0;
    const char *p;

    memset(&s_ti, 0, sizeof s_ti);
    snprintf(s_ti.title, sizeof s_ti.title, "%s", r->title);
    snprintf(s_ti.artist, sizeof s_ti.artist, "%s", r->artist);
    snprintf(s_ti.album, sizeof s_ti.album, "%s", r->album);
    snprintf(s_ti.genre, sizeof s_ti.genre, "%s", r->genre);
    snprintf(s_ti.path, sizeof s_ti.path, "/%s", r->path);
    s_ti.duration_ms = r->duration_ms ? (long)r->duration_ms : 215000;
    for (p = r->title; *p; p++) h = h * 31u + (unsigned char)*p;
    s_ti.bits = (h & 1u) ? 24 : 16;
    s_ti.sample_rate = (h & 1u) ? ((h & 2u) ? 96000 : 48000) : 44100;
    if (strstr(r->path, ".mp3")) { s_ti.bits = 16; s_ti.sample_rate = 44100; }
    s_ti.playlist_pos = s_n ? s_pos + 1 : 0;
    s_ti.playlist_count = s_n;
    s_have = 1;
}

static int open_index(int i)
{
    media_rec_t r;
    int was_open = media_db_is_open();

    if (!was_open && media_db_open() != FS_OK)
        return PLAYER_ERR;
    if (media_db_get(s_q[i], &r) != FS_OK) {
        if (!was_open) media_db_close();
        return PLAYER_ERR;
    }
    if (!was_open) media_db_close();
    s_pos = i;
    fill_from_rec(&r);
    s_pos_ms = 0;
    fire(PLAYER_EV_TRACK);
    return PLAYER_OK;
}

/* ---- called by the simulator loop ------------------------------------- */
void sim_player_advance(unsigned dt_ms)
{
    if (s_state != PLAYER_PLAYING || !s_have)
        return;
    s_pos_ms += (long)dt_ms;
    if (s_pos_ms < s_ti.duration_ms)
        return;
    if (s_repeat == 2) { s_pos_ms = 0; return; }
    if (s_n && (s_pos + 1 < s_n || s_repeat == 1 || s_shuffle)) {
        (void)player_next();
        return;
    }
    s_state = PLAYER_STOPPED;
    s_pos_ms = 0;
    fire(PLAYER_EV_END_OF_TRACK);
    fire(PLAYER_EV_STATE);
}

/* ---- player API -------------------------------------------------------- */
int  player_init(void) { return PLAYER_OK; }
int  player_process(void) { return 0; }
void player_set_callback(player_event_fn fn, void *user) { s_cb = fn; s_cb_user = user; }
void player_set_resolver(int (*fn)(uint16_t, char *, int)) { s_resolve = fn; }

int player_open(const char *path)
{
    /* a file from the browser: find its record, else build from the name */
    media_rec_t r;
    uint32_t i, n;
    const char *p = path[0] == '/' ? path + 1 : path;

    s_n = 0;
    if (media_db_open() == FS_OK) {
        n = media_db_count();
        for (i = 0; i < n; i++)
            if (media_db_get(i, &r) == FS_OK && strcmp(r.path, p) == 0) {
                media_db_close();
                fill_from_rec(&r);
                s_pos_ms = 0;
                fire(PLAYER_EV_TRACK);
                return PLAYER_OK;
            }
        media_db_close();
    }
    memset(&r, 0, sizeof r);
    snprintf(r.path, sizeof r.path, "%s", p);
    {
        const char *b = strrchr(p, '/');
        snprintf(r.title, sizeof r.title, "%s", b ? b + 1 : p);
    }
    fill_from_rec(&r);
    fire(PLAYER_EV_TRACK);
    return PLAYER_OK;
}

int player_play(void)
{
    if (!s_have) return PLAYER_ERR_EMPTY;
    s_state = PLAYER_PLAYING; fire(PLAYER_EV_STATE); return PLAYER_OK;
}
int player_pause(void)
{
    if (s_state != PLAYER_PLAYING) return PLAYER_ERR_STATE;
    s_state = PLAYER_PAUSED; fire(PLAYER_EV_STATE); return PLAYER_OK;
}
int player_stop(void) { s_state = PLAYER_STOPPED; fire(PLAYER_EV_STATE); return PLAYER_OK; }
int player_seek(long ms)
{
    if (!s_have) return PLAYER_ERR_EMPTY;
    if (ms < 0) ms = 0;
    if (ms > s_ti.duration_ms - 500) ms = s_ti.duration_ms - 500;
    s_pos_ms = ms; return PLAYER_OK;
}
int player_next(void)
{
    int i;
    if (!s_n) return PLAYER_ERR_EMPTY;
    if (s_shuffle) i = rand() % s_n;
    else if (s_pos + 1 < s_n) i = s_pos + 1;
    else if (s_repeat == 1) i = 0;
    else return PLAYER_ERR_EMPTY;
    if (open_index(i) != PLAYER_OK) return PLAYER_ERR;
    if (s_state != PLAYER_PLAYING) { s_state = PLAYER_PLAYING; fire(PLAYER_EV_STATE); }
    return PLAYER_OK;
}
int player_prev(void)
{
    if (!s_n) return PLAYER_ERR_EMPTY;
    if (s_pos_ms > 3000 || s_pos == 0) { s_pos_ms = 0; return PLAYER_OK; }
    return open_index(s_pos - 1);
}
int  player_get_state(void) { return s_state; }
long player_get_position_ms(void) { return s_have ? s_pos_ms : 0; }
int  player_set_volume(int db)
{
    if (db < -60) db = -60;
    if (db > 0) db = 0;
    s_vol = db; return PLAYER_OK;
}
int  player_get_volume(void) { return s_vol; }
int  player_get_track(track_info_t *out)
{
    if (!s_have) return PLAYER_ERR_EMPTY;
    *out = s_ti;
    out->playlist_pos = s_n ? s_pos + 1 : 0;
    out->playlist_count = s_n;
    return PLAYER_OK;
}
void player_set_fade_ms(int ms) { (void)ms; }
void player_set_shuffle(int on) { s_shuffle = on; }
int  player_get_shuffle(void) { return s_shuffle; }
void player_set_repeat(int m) { s_repeat = m; }
int  player_get_repeat(void) { return s_repeat; }
void player_set_replaygain_mode(int m) { s_rg = m; }
int  player_get_replaygain_mode(void) { return s_rg; }

int player_play_list(const uint16_t *idx, int n, int start)
{
    if (n <= 0) return PLAYER_ERR_EMPTY;
    if (n > QMAX) n = QMAX;
    memcpy(s_q, idx, (size_t)n * sizeof *idx);
    s_n = n;
    if (start < 0 || start >= n) start = 0;
    if (open_index(start) != PLAYER_OK) return PLAYER_ERR;
    s_state = PLAYER_PLAYING;
    fire(PLAYER_EV_STATE);
    return PLAYER_OK;
}
int player_load_list(const uint16_t *idx, int n, int start)
{
    int rc = player_play_list(idx, n, start);
    s_state = PLAYER_PAUSED;
    return rc;
}
int player_play_at(int index)
{
    if (index < 0 || index >= s_n) return PLAYER_ERR;
    if (open_index(index) != PLAYER_OK) return PLAYER_ERR;
    s_state = PLAYER_PLAYING; fire(PLAYER_EV_STATE);
    return PLAYER_OK;
}
int player_list_count(void) { return s_n; }
int player_list_position(void) { return s_n ? s_pos : -1; }
int player_list_title(int index, char *buf, int cap)
{
    media_rec_t r;
    int was_open = media_db_is_open();

    if (index < 0 || index >= s_n) return PLAYER_ERR;
    if (!was_open && media_db_open() != FS_OK) return PLAYER_ERR;
    if (media_db_get(s_q[index], &r) != FS_OK) { if (!was_open) media_db_close(); return PLAYER_ERR; }
    if (!was_open) media_db_close();
    snprintf(buf, (size_t)cap, "%s", r.title);
    return PLAYER_OK;
}
void player_set_queue_source(int kind, const char *value, int cat)
{
    s_qkind = kind; s_qcat = cat;
    snprintf(s_qval, sizeof s_qval, "%s", value ? value : "");
}
void player_get_queue_source(int *kind, char *value, int cap, int *cat)
{
    if (kind) *kind = s_qkind;
    if (value) snprintf(value, (size_t)cap, "%s", s_qval);
    if (cat) *cat = s_qcat;
}

/* diagnostics the browser screen reads after a failed open */
unsigned flac_diag_block, flac_diag_channels;
unsigned long flac_diag_need;
int flac_diag_reason;
