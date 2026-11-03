/*
 * hw.c — devsim: the Echo Mini hardware under the real AP firmware.
 *
 * The AP firmware (ap_ui.c, player, ipc_b_target, bfs, audio_output, UI...)
 * is compiled natively. Under it:
 *   - Core B is the REAL bb_core.bin, executed by unicorn on the same host
 *     memory the AP sees at 0x01000000 (shared block, file rings, PCM ring);
 *   - the I2S1 TX FIFO + its TX-empty IRQ are modelled per millisecond
 *     (FIFO drains at the sample rate, the ISR tops it up from the ring,
 *     masks itself when the ring is dry; B or rknano_i2s_kick re-arm it);
 *   - the DAC tracks power, volume attenuation, hardware mute and amp
 *     enable, so "audible" means what it means on the device;
 *   - storage is fs_host (a directory), keys are a scripted ADC ladder,
 *     board_power_off ends the process (exit 77 = powered off).
 * Time is simulated: 1 tick = 1 ms; every delay advances it.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/mman.h>
#include <sys/stat.h>

#include "drivers/display.h"
#include "drivers/core_b.h"
#include "drivers/jack.h"
#include "drivers/usb_msc.h"
#include "drivers/usb_dac.h"
#include "drivers/rknano_i2s.h"
#include "drivers/cs43131.h"
#include "services/fs.h"
#include "services/fs_host.h"
#include "services/fs_target.h"
#include "drivers/emmc.h"
#include "drivers/bt_hw.h"
#include "services/fw_update.h"
#include "devsim.h"

/* ------------------------------------------------------------ globals */
devsim_t DS;

/* ------------------------------------------------------------ unicorn */
typedef void uc_engine;
static int (*p_uc_open)(int, int, uc_engine **);
static int (*p_uc_mem_map_ptr)(uc_engine *, uint64_t, size_t, uint32_t, void *);
static int (*p_uc_reg_write)(uc_engine *, int, const void *);
static int (*p_uc_reg_read)(uc_engine *, int, void *);
static int (*p_uc_emu_start)(uc_engine *, uint64_t, uint64_t, uint64_t, size_t);
static const char *(*p_uc_strerror)(int);
static uc_engine *s_uc;
static uint32_t s_b_pc;
static uint8_t *s_bmem = (uint8_t *)0x01000000;
static uint32_t *s_i2s = (uint32_t *)0x40030000;   /* host page = B's I2S page */
static unsigned char s_blob[0x20000];
static unsigned s_blob_len;

#define UC_ARCH_ARM 1
#define UC_MODE_THUMB 16
#define UC_MODE_MCLASS 32
#define UC_PROT_ALL 7
#define UC_ARM_REG_PC 11
#define UC_ARM_REG_SP 12

static void map_fixed(uintptr_t a, size_t n)
{
    void *p = mmap((void *)a, n, PROT_READ | PROT_WRITE,
                   MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p != (void *)a) {
        fprintf(stderr, "devsim: mmap %lx failed\n", (unsigned long)a);
        exit(2);
    }
}

static void uc_setup(void)
{
    void *h = dlopen(getenv("UNICORN_SO") ? getenv("UNICORN_SO") :
                     "/usr/local/lib/python3.13/site-packages/unicorn/lib/libunicorn.so.2",
                     RTLD_NOW);
    FILE *f;

    if (!h) { fprintf(stderr, "devsim: %s\n", dlerror()); exit(2); }
    p_uc_open = dlsym(h, "uc_open");
    p_uc_mem_map_ptr = dlsym(h, "uc_mem_map_ptr");
    p_uc_reg_write = dlsym(h, "uc_reg_write");
    p_uc_reg_read = dlsym(h, "uc_reg_read");
    p_uc_emu_start = dlsym(h, "uc_emu_start");
    p_uc_strerror = dlsym(h, "uc_strerror");
    if (p_uc_open(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS, &s_uc) ||
        p_uc_mem_map_ptr(s_uc, 0x01000000, 0x60000, UC_PROT_ALL, s_bmem) ||
        p_uc_mem_map_ptr(s_uc, 0x40030000, 0x1000, UC_PROT_ALL, s_i2s)) {
        fprintf(stderr, "devsim: unicorn setup failed\n");
        exit(2);
    }
    f = fopen(getenv("BB_BIN") ? getenv("BB_BIN") : "bb_core.bin", "rb");
    if (!f) { fprintf(stderr, "devsim: no bb_core.bin\n"); exit(2); }
    s_blob_len = (unsigned)fread(s_blob, 1, sizeof s_blob, f);
    fclose(f);
}

static void b_run(size_t n)
{
    int e;

    if (!DS.b_running || n == 0)
        return;
    e = p_uc_emu_start(s_uc, s_b_pc | 1u, 0xFFFFFFFFull, 0, n);
    if (e) {
        uint32_t pc;
        p_uc_reg_read(s_uc, UC_ARM_REG_PC, &pc);
        fprintf(stderr, "devsim: CORE B FAULT %s at %08x\n", p_uc_strerror(e), pc);
        DS.b_faults++;
        DS.b_running = 0;
        return;
    }
    p_uc_reg_read(s_uc, UC_ARM_REG_PC, &s_b_pc);
    DS.b_insns += n;
}

int ap_core_b_start(void)
{
    uint32_t sp, pc;
    int i;

    memcpy(s_bmem, s_blob, s_blob_len);
    ((volatile uint32_t *)0x01020000)[0] = 0;
    memcpy(&sp, s_blob, 4);
    memcpy(&pc, s_blob + 4, 4);
    p_uc_reg_write(s_uc, UC_ARM_REG_SP, &sp);
    s_b_pc = pc & ~1u;
    DS.b_running = 1;
    DS.b_starts++;
    for (i = 0; i < 200 && ((volatile uint32_t *)0x01020000)[0] != 0x42524459u; i++)
        b_run(20000);
    return ((volatile uint32_t *)0x01020000)[0] == 0x42524459u ? 0 : -1;
}
uint32_t ap_core_b_magic(void) { return ((volatile uint32_t *)0x01020000)[0]; }
void ap_core_b_stop(void) { DS.b_running = 0; DS.b_stops++; }
int ap_core_b_running(void) { return DS.b_running; }

/* ------------------------------------------------------------ I2S + DAC */
#define I2S_INTCR_W 5            /* 0x14 / 4 */
static rknano_i2s_pull_fn s_pull;
static void *s_pull_user;
static int s_hold, s_xfer;
static uint32_t s_rate = 44100;
static int s_fifo;               /* frames in the TX FIFO (14 max) */
static unsigned s_rate_acc;

void rknano_i2s_attach(rknano_i2s_pull_fn pull, void *user) { s_pull = pull; s_pull_user = user; s_hold = 0; }
void rknano_i2s_detach(void) { s_i2s[I2S_INTCR_W] &= ~1u; s_pull = 0; }
void rknano_i2s_kick(void) { if (s_pull && !s_hold) s_i2s[I2S_INTCR_W] |= 1u; }
void rknano_i2s_hold(int held) { s_hold = held ? 1 : 0; if (held) s_i2s[I2S_INTCR_W] &= ~1u; else rknano_i2s_kick(); }
void rknano_i2s_start(void) { s_xfer = 1; }
void rknano_i2s_stop(void) { s_xfer = 0; s_fifo = 0; }
int rknano_i2s_feed(const int16_t *pcm, int frames) { (void)pcm; return frames; }
void i2s1_setup(uint32_t rate, uint32_t mclk) { (void)mclk; s_rate = rate; DS.rate = rate; }
void acodec_mux(uint8_t a, uint8_t b, uint8_t c, uint8_t d) { }

int s_step;
uint8_t s_hp_status[2];
const dac_mono_pair_t dac_mono_seq[24];
static uint8_t s_atten = 0xFF;
static int s_gpio_mute = 1, s_amp;
static int s_dac_powered;

int dac_map_write_chan(int chan, uint32_t map24, uint8_t val) { return 0; }
int dac_map_write(uint32_t map24, uint8_t val) { return 0; }
int dac_map_read(int chan, uint32_t map24, uint8_t *out) { if (out) *out = 0; return 0; }
void dac_pdn_up(uint8_t mask) { }
void dac_volume_set(uint8_t atten) { s_atten = atten; }
int devsim_atten(void) { return s_atten; }
void dac_volume_ramp(uint8_t from, uint8_t to) { s_atten = to; }
void dac_volume_ramp_ms(uint8_t from, uint8_t to, unsigned ms) { dac_delay_ms(ms); s_atten = to; }
void dac_power_sequence(void) { s_dac_powered = 1; }
int i2c0_scan(void) { return 0; }
void dac_output_off(void) { s_dac_powered = 0; s_amp = 0; }
void dac_gpio_out(int port, int pin, int level)
{
    if (port == 2 && pin == 0) s_gpio_mute = level;
    if (port == 1 && pin == 4) s_amp = level;
}
void dac_gpio_input(int port, int pin) { }
void cru_gate(int g, int en) { }
void cru_rst(int r, int a) { }
void grf_iomux(int port, int pin, int func) { }

int devsim_audible(void)
{
    return s_xfer && s_atten < 0xF0 && !s_gpio_mute && s_amp;
}

/* one millisecond of I2S */
static void i2s_ms(void)
{
    unsigned n;

    s_rate_acc += s_rate;
    n = s_rate_acc / 1000u;
    s_rate_acc %= 1000u;
    if (!s_xfer)
        return;
    while (n--) {
        /* ISR keeps the FIFO topped while unmasked */
        if ((s_i2s[I2S_INTCR_W] & 1u) && s_pull && !s_hold) {
            while (s_fifo < 14) {
                uint32_t l, r;

                if (!s_pull(&l, &r, s_pull_user)) {
                    s_i2s[I2S_INTCR_W] &= ~1u;      /* dry: mask */
                    break;
                }
                s_fifo++;
                if (devsim_audible()) {
                    extern long long g_zc;
                    static int prev_neg;
                    int32_t sl = (int32_t)l >> 16;
                    int neg = sl < 0;

                    DS.win_energy += (double)sl * sl;
                    {
                        static FILE *pf; static int tried;
                        if (!tried) { const char *e = getenv("DEVSIM_PCM"); tried = 1; if (e) pf = fopen(e, "wb"); }
                        if (pf) { int16_t v = (int16_t)sl; fwrite(&v, 2, 1, pf); }
                    }
                    if (neg != prev_neg && (sl > 300 || sl < -300)) {
                        g_zc++;
                        prev_neg = neg;
                    }
                }
            }
        }
        if (s_fifo > 0) {
            s_fifo--;
            DS.frames_out++;
            if (devsim_audible())
                DS.frames_audible++;
        } else {
            DS.frames_gap++;
        }
    }
}

/* ------------------------------------------------------------ time */
void SysTick_Handler(void);
static unsigned s_us_acc;
#define B_INSN_PER_MS 60000u

static void tick_ms(void)
{
    DS.now_ms++;
    SysTick_Handler();
    b_run(B_INSN_PER_MS);
    i2s_ms();
    devsim_scenario_tick();
}

static void advance_us(unsigned us)
{
    s_us_acc += us;
    while (s_us_acc >= 1000u) {
        s_us_acc -= 1000u;
        tick_ms();
    }
}

#include "ui/ui.h"
void host_wfi(void)
{
    static unsigned last;
    if (last && DS.now_ms - last > 60) {
        const ui_screen_t *t = ui_top_screen();
        printf("  BLOCK %4u ms at t=%.1fs top=%s\n", DS.now_ms - last, DS.now_ms / 1000.0, t && t->name ? t->name : "-");
    }
    tick_ms();
    last = DS.now_ms;
}
void panel_io_delay_ms(uint16_t ms) { while (ms--) tick_ms(); }
static unsigned (*s_dclock)(void);
static void (*s_dpump)(void);
void dac_delay_set_clock(unsigned (*ms)(void)) { s_dclock = ms; }
void dac_delay_set_pump(void (*fn)(void)) { s_dpump = fn; }
void dac_delay_ms(unsigned ms)
{
    while (ms--) {
        tick_ms();
        if (s_dpump)
            s_dpump();
    }
}
void delay_loops(volatile unsigned n)
{
    /* ~200 loops per microsecond on the device; also let B run that long */
    unsigned us = n / 200u + 1u;

    b_run((size_t)us * (B_INSN_PER_MS / 1000u));
    advance_us(us);
}

/* ------------------------------------------------------------ keys, power */
int keys_adc(void) { return DS.key_adc; }
int keys_power(void) { return DS.key_power; }
void keys_scan_tick(void) { }
int keys_scan_take(int *adc, int *power)
{
    if (DS.now_ms % 5u)
        return 0;
    *adc = DS.key_adc;
    *power = DS.key_power;
    return 1;
}
int keys_scan_failed(void) { return 0; }
int adc_read_channel(int ch) { return ch == 0 ? DS.batt_adc : DS.key_adc; }
void backlight_on(void) { DS.backlight = 1; }
void backlight_off(void) { DS.backlight = 0; }
void backlight_set_level(int level) { }
void board_power_off(void)
{
    DS.powered_off = 1;
    devsim_on_power_off();
    exit(77);
}

/* ------------------------------------------------------------ storage etc */
int emmc_init(void) { return 0; }
int emmc_layout(uint32_t *user_start) { if (user_start) *user_start = 0; return 0; }
int emmc_read(uint32_t lba, uint32_t n, void *buf) { return -1; }
int emmc_write(uint32_t lba, uint32_t n, const void *buf) { return -1; }
uint32_t emmc_sectors(void) { return 1u << 22; }
int sd_present(void) { return DS.sd_in; }
int sd_init(void) { return 0; }
int sd_read(uint32_t lba, uint32_t n, void *buf) { return -1; }
uint32_t sd_sectors(void) { return 1u << 22; }
int sd_is_hc(void) { return 1; }
int sd_bus_width(void) { return 4; }
int fs_target_mount(int idx, const char *name, fs_block_read_t rd, uint32_t base) { return 0; }
void fs_target_unmount(int idx) { }
const char *fs_target_type(int idx) { return "FAT32"; }
int fs_target_set_writer(int idx, fs_block_write_t wr) { return 0; }
int fs_target_mkdir(const char *path)
{
    char p[512];

    snprintf(p, sizeof p, "%s%s", fs_host_get_root(), path);
    return mkdir(p, 0777) == 0 ? 0 : 0;
}
int usb_cable(void) { return DS.usb; }
uint32_t usb_msc_diag;
int usb_msc_run(const usb_lun_t *luns, unsigned nluns, int (*user_exit)(void),
                uint32_t *rd, uint32_t *wr) { if (rd) *rd = 0; if (wr) *wr = 0; return 0; }
int usb_dac_run(int (*user_exit)(void), usb_dac_diag_t *diag) { return 0; }
int fw_update_find(uint32_t vol_lba, fw_image_t *img, fwu_progress_t progress) { return -1; }
int fw_update_install(const fw_image_t *img, fwu_progress_t progress) { return -1; }
int fw_update_retire(const fw_image_t *img) { return -1; }

/* jack: headphones in (single-ended) unless the scenario pulls them */
static int s_jack_reported = -1;
void jack_init(void) { }
int jack_poll(jack_kind_t *out)
{
    jack_kind_t k = DS.jack_out ? JACK_NONE : JACK_SINGLE_ENDED;

    if ((int)k == s_jack_reported)
        return 0;
    s_jack_reported = (int)k;
    *out = k;
    return 1;
}
void jack_raw(int *se, int *bal) { *se = DS.jack_out ? 1 : 0; *bal = 1; }
jack_kind_t jack_current(void) { return DS.jack_out ? JACK_NONE : JACK_SINGLE_ENDED; }

/* bluetooth module: absent/off */
void bt_hw_power_on(void) { }
void bt_hw_power_off(void) { }
int bt_hw_powered(void) { return 0; }
int bt_hw_read(void) { return -1; }
int bt_hw_write(const uint8_t *buf, unsigned len) { return (int)len; }
void bt_hw_route(int on) { }
int bt_hw_routed(void) { return 0; }
int bt_hw_settling(void) { return 0; }

/* ------------------------------------------------------------ boot */
void ap_ui_loop(void);
void display_init(void);

void devsim_boot(int argc, char **argv)
{
    map_fixed(0x01000000, 0x60000);
    map_fixed(0x40000000, 0x200000);
    map_fixed(0x50000000, 0x20000);
    map_fixed(0xE000E000, 0x1000);
    uc_setup();
    fs_host_set_root(DS.root[0] ? DS.root : ".");
    DS.batt_adc = 800;
    DS.key_adc = 1023;
    DS.jack_out = 0;
    DS.sd_in = 1;
    devsim_scenario_init(argc, argv);
    display_init();
    (void)ap_core_b_start();
    ap_ui_loop();
}

void devsim_log(const char *line)
{
    if (DS.quiet < 2)
        fprintf(stderr, "[%7u] %s\n", DS.now_ms, line);
}

/* theme files open device paths with stdio: map them under the root */
FILE *devsim_fopen(const char *path, const char *mode)
{
    char p[600];

    snprintf(p, sizeof p, "%s%s", DS.root, path);
    return fopen(p, mode);
}

/* ---- device costs: the panel bus and the eMMC are not free ------------- */
static unsigned s_cost_ns;
static void cost_ns(unsigned ns)
{
    s_cost_ns += ns;
    if (s_cost_ns >= 1000u) {
        unsigned us = s_cost_ns / 1000u;

        s_cost_ns %= 1000u;
        b_run((size_t)us * (B_INSN_PER_MS / 1000u));
        advance_us(us);
    }
}
void psim_send_pixel(uint16_t rgb565);
void panel_io_send_pixel(uint16_t rgb565)
{
    psim_send_pixel(rgb565);
    cost_ns(300);                         /* ~16 ms per full frame */
}
long fsh_read(fs_file_t *f, void *buf, unsigned long cap);
fs_file_t *fsh_open_read(const char *path);
long fs_read(fs_file_t *f, void *buf, unsigned long cap)
{
    cost_ns((unsigned)(cap / 512u + 1u) * 60000u);   /* ~60 us per sector */
    return fsh_read(f, buf, cap);
}
fs_file_t *fs_open_read(const char *path)
{
    cost_ns(1500000u);                    /* directory walk */
    return fsh_open_read(path);
}
