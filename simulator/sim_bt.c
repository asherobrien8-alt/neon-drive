/* sim_bt.c — no Bluetooth radio in the simulator: the Settings > Bluetooth
 * screen runs against this inert stand-in (taken from ReChord's UI test mock). */
#include <stdio.h>
#include <string.h>
/* ---- Bluetooth (services/bt_link.c) ------------------------------------
 * The screen is exercised against a scripted policy: no UART, no module. */
#include "services/bt_link.h"

static bt_proto_t     s_mock_bt;
static int            s_mock_bt_on;
static int            s_mock_bt_actions;
static int            s_mock_bt_last_device;
static int            s_mock_bt_screen_opens;
static unsigned long  s_mock_now = 1000UL;

void mock_bt_reset(void)
{
    memset(&s_mock_bt, 0, sizeof s_mock_bt);
    s_mock_bt.state = BT_STATE_OFF;
    s_mock_bt.connected = -1;
    s_mock_bt.target = -1;
    s_mock_bt_on = 0;
    s_mock_bt_actions = 0;
    s_mock_bt_last_device = -1;
    s_mock_bt_screen_opens = 0;
    s_mock_now = 1000UL;
}

void mock_bt_set(int on, int state, int count)
{
    s_mock_bt_on = on ? 1 : 0;
    s_mock_bt.state = (bt_state_t)state;
    s_mock_bt.count = (uint8_t)count;
}

void mock_bt_set_device(int index, const char *name)
{
    if (index < 0 || index >= BT_DEV_MAX)
        return;
    snprintf(s_mock_bt.devices[index].name, BT_NAME_MAX, "%s", name);
    s_mock_bt.devices[index].addr[0] = (uint8_t)index;
}

int mock_bt_action_count(void) { return s_mock_bt_actions; }
int mock_bt_last_device(void) { return s_mock_bt_last_device; }
int mock_bt_screen_opens(void) { return s_mock_bt_screen_opens; }

unsigned long log_now_ms(void) { return s_mock_now; }

const bt_proto_t *bt_link_state(void) { return &s_mock_bt; }
int  bt_link_enabled(void) { return s_mock_bt_on; }

void bt_link_set_enabled(int on, unsigned long now)
{
    s_mock_bt_on = on ? 1 : 0;
    s_mock_bt.state = on ? BT_STATE_STARTING : BT_STATE_OFF;
    s_mock_bt_actions++;
    s_mock_now = now;
}

void bt_link_screen_opened(unsigned long now)
{
    s_mock_bt_screen_opens++;
    s_mock_now = now;
}

void bt_link_screen_closed(unsigned long now) { s_mock_now = now; }

void bt_link_scan(unsigned long now)
{
    s_mock_bt_actions++;
    s_mock_bt.state = BT_STATE_SCANNING;
    s_mock_now = now;
}

void bt_link_connect(int device, unsigned long now)
{
    s_mock_bt_actions++;
    s_mock_bt_last_device = device;
    s_mock_bt.state = BT_STATE_CONNECTING;
    s_mock_bt.target = (int8_t)device;
    s_mock_now = now;
}

void bt_link_disconnect(unsigned long now)
{
    s_mock_bt_actions++;
    s_mock_now = now;
}

void bt_link_forget(int device, unsigned long now)
{
    s_mock_bt_actions++;
    s_mock_bt_last_device = device;
    s_mock_now = now;
}

const char *bt_link_status_text(void)
{
    return s_mock_bt_on ? "On" : "Off";
}
