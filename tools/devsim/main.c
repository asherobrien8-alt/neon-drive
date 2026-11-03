/*
 * main.c — devsim scenario runner.
 *
 *   devsim <root> <script>
 *
 * Script lines (one per line, # comments):
 *   wait MS                 let the device run
 *   press KEY [MS]          tap a key (UP DOWN SEL BACK MENU POWER), default 120 ms
 *   hold KEY MS             hold a key
 *   shot NAME               write NAME.ppm (what the panel shows)
 *   mark TEXT               print a marker into the report
 *   listen MS               run MS and report each second: state, track,
 *                           audible %, tone (Hz) — the tone identifies the song
 *   jack out|in             pull / insert the headphones
 *   usb on|off              cable
 * A power-off (exit 77) saves the line number; the runner restarts devsim,
 * which boots (holding POWER) and continues after the line that turned it off.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "devsim.h"
#include "player/player.h"
#include "ui/ui.h"
#include "drivers/panel_io_sim.h"

void devsim_boot(int argc, char **argv);

static char s_lines[400][128];
static int s_n, s_pc;
static unsigned s_wait_until;
static int s_key_release_at;
static int s_boot_hold = 1;
static char s_state_path[300];

/* listening */
static int s_listen_left;           /* seconds still to report */
static unsigned long long s_l_frames, s_l_aud;
static unsigned s_l_t0;
long long g_zc;                     /* zero crossings (hw.c) */

static int key_adc(const char *k)
{
    if (!strcmp(k, "DOWN")) return 30;
    if (!strcmp(k, "UP")) return 120;
    if (!strcmp(k, "SEL")) return 250;
    if (!strcmp(k, "MENU")) return 360;
    if (!strcmp(k, "BACK")) return 500;
    return -1;
}

static const char *state_name(int s)
{
    switch (s) {
    case PLAYER_STOPPED: return "STOP";
    case PLAYER_PLAYING: return "PLAY";
    case PLAYER_PAUSED: return "PAUS";
    case PLAYER_ERROR: return "ERR ";
    default: return "?";
    }
}

static char s_ft[32][48];
static int s_fv[32], s_fn;

static int expect_freq(const char *title)
{
    int i;

    if (s_fn == 0) {
        FILE *f = fopen("freqs.txt", "r");
        char b[96];

        while (f && fgets(b, sizeof b, f) && s_fn < 32) {
            char *bar = strchr(b, '|');
            if (!bar) continue;
            *bar = 0;
            snprintf(s_ft[s_fn], 48, "%s", b);
            s_fv[s_fn++] = atoi(bar + 1);
        }
        if (f) fclose(f);
    }
    for (i = 0; i < s_fn; i++)
        if (strstr(title, s_ft[i]) && (strlen(s_ft[i]) + 3 >= strlen(title)))
            return s_fv[i];
    return 0;
}

int devsim_atten(void);
static void report_second(void)
{
    track_info_t ti;
    const ui_screen_t *top = ui_top_screen();
    unsigned long long fr = DS.frames_out - s_l_frames, au = DS.frames_audible - s_l_aud;
    double hz = 0;
    unsigned dt = DS.now_ms - s_l_t0;

    unsigned rate = DS.rate ? DS.rate : 44100;
    int exp, verdict;

    if (au > 0)
        hz = (double)g_zc / 2.0 / ((double)au / rate);
    if (player_get_track(&ti) != PLAYER_OK)
        ti.title[0] = 0;
    exp = expect_freq(ti.title);
    verdict = (player_get_state() != PLAYER_PLAYING) ? ' ' :
              (exp && hz > exp * 0.97 && hz < exp * 1.03 &&
               au * 1000 >= (unsigned long long)dt * rate * 9 / 10) ? '+' : '!';
    printf("  t=%6.1fs %c %s  %-16.16s list %2d/%-2d  audio %3d%%  tone %5.0f/%4d Hz  %5uHz v%2d/a%3d p%5.1f [%s]\n",
           DS.now_ms / 1000.0, verdict, state_name(player_get_state()), ti.title,
           player_list_position() + 1, player_list_count(),
           dt ? (int)(au * 100000 / ((unsigned long long)dt * rate)) : 0, hz, exp, rate, player_get_volume(), devsim_atten(), player_get_position_ms() / 1000.0,
           top && top->name ? top->name : "-");
    fflush(stdout);
    s_l_frames = DS.frames_out;
    s_l_aud = DS.frames_audible;
    s_l_t0 = DS.now_ms;
    g_zc = 0;
}

static void save_pc(void)
{
    FILE *f = fopen(s_state_path, "w");

    if (f) { fprintf(f, "%d\n", s_pc); fclose(f); }
}

void devsim_on_power_off(void)
{
    printf("  -- powered off at t=%.1fs (line %d)\n", DS.now_ms / 1000.0, s_pc);
    save_pc();
}

void devsim_scenario_init(int argc, char **argv)
{
    FILE *f;
    char buf[256];

    (void)argc;
    f = fopen(argv[2], "r");
    if (!f) { perror(argv[2]); exit(2); }
    while (fgets(buf, sizeof buf, f) && s_n < 400) {
        buf[strcspn(buf, "\r\n")] = 0;
        snprintf(s_lines[s_n++], 128, "%s", buf);
    }
    fclose(f);
    snprintf(s_state_path, sizeof s_state_path, "%s/.devsim_pc", argv[1]);
    f = fopen(s_state_path, "r");
    if (f) {
        if (fscanf(f, "%d", &s_pc) != 1) s_pc = 0;
        fclose(f);
        remove(s_state_path);
    }
    printf("== boot (script line %d)\n", s_pc);
    DS.key_power = 1;                /* the user holds POWER to switch on */
    s_boot_hold = 1;
}

void devsim_scenario_tick(void)
{
    char cmd[32], a1[96];
    int n1;

    if (s_boot_hold && DS.now_ms >= 1500) {
        DS.key_power = 0;
        s_boot_hold = 0;
    }
    if (s_key_release_at && DS.now_ms >= (unsigned)s_key_release_at) {
        DS.key_adc = 1023;
        DS.key_power = 0;
        s_key_release_at = 0;
    }
    if (s_listen_left > 0 && DS.now_ms - s_l_t0 >= 1000) {
        report_second();
        s_listen_left--;
    }
    if (DS.now_ms < s_wait_until || s_key_release_at || s_boot_hold)
        return;
    while (s_pc < s_n) {
        const char *l = s_lines[s_pc++];

        cmd[0] = a1[0] = 0;
        n1 = 0;
        if (l[0] == '#' || l[0] == 0)
            continue;
        sscanf(l, "%31s %95s %d", cmd, a1, &n1);
        if (!strcmp(cmd, "wait")) {
            s_wait_until = DS.now_ms + (unsigned)atoi(a1);
            return;
        }
        if (!strcmp(cmd, "press") || !strcmp(cmd, "hold")) {
            int ms = n1 > 0 ? n1 : 120;

            if (!strcmp(a1, "POWER"))
                DS.key_power = 1;
            else
                DS.key_adc = key_adc(a1);
            s_key_release_at = (int)(DS.now_ms + (unsigned)ms);
            s_wait_until = DS.now_ms + (unsigned)ms + 150u;
            return;
        }
        if (!strcmp(cmd, "listen")) {
            int ms = atoi(a1);

            s_listen_left = ms / 1000;
            s_l_frames = DS.frames_out;
            s_l_aud = DS.frames_audible;
            s_l_t0 = DS.now_ms;
            g_zc = 0;
            s_wait_until = DS.now_ms + (unsigned)ms + 5u;
            return;
        }
        if (!strcmp(cmd, "mark")) {
            printf("## %s\n", l + 5);
            continue;
        }
        if (!strcmp(cmd, "shot")) {
            char p[300];

            snprintf(p, sizeof p, "shots/%s.ppm", a1);
            panel_io_sim_write_ppm(p);
            continue;
        }
        if (!strcmp(cmd, "jack")) {
            DS.jack_out = !strcmp(a1, "out");
            continue;
        }
        if (!strcmp(cmd, "usb")) {
            DS.usb = !strcmp(a1, "on");
            continue;
        }
        if (!strcmp(cmd, "end"))
            break;
        printf("?? %s\n", l);
    }
    if (s_pc >= s_n) {
        printf("== script done at t=%.1fs  (B starts %d, faults %d, gaps %llu frames)\n",
               DS.now_ms / 1000.0, DS.b_starts, DS.b_faults, DS.frames_gap);
        exit(DS.b_faults ? 3 : 0);
    }
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: devsim ROOT SCRIPT\n");
        return 2;
    }
    snprintf(DS.root, sizeof DS.root, "%s", argv[1]);
    DS.quiet = getenv("DEVSIM_QUIET") ? atoi(getenv("DEVSIM_QUIET")) : 0;
    devsim_boot(argc, argv);
    return 0;
}
