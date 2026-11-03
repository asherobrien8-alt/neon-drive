#ifndef DEVSIM_H
#define DEVSIM_H
#include <stdint.h>
typedef struct {
    char root[256];
    unsigned now_ms;
    int key_adc, key_power, batt_adc, jack_out, sd_in, usb, backlight;
    int b_running, b_starts, b_stops, b_faults, powered_off;
    unsigned long long b_insns;
    unsigned long long frames_out, frames_audible, frames_gap;
    double win_energy;
    int quiet;
    unsigned rate;
    int bad;
} devsim_t;
extern devsim_t DS;
int devsim_audible(void);
void devsim_scenario_init(int argc, char **argv);
void devsim_scenario_tick(void);
void devsim_on_power_off(void);
#endif
