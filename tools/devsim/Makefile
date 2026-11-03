F ?= $(abspath ../../firmware/.rechord-src/firmware)
CC = cc
CFLAGS = -g -O1 -w -std=gnu99 -fcommon -DRECHORD_AP_BUILD -DAP_DEBUG_TOOLS=0 -DAP_MEM_PROBE=0 \
  -DAP_MEM_OVERLAY=0 -DAP_CDC_OVERLAY=0 -DRECHORD_AP_METADATA_ONLY=1 -DLOG_BUFFER_LINES=40 \
  -DFS_HOST_HAVE_DIRENT -I$(F) -I$(F)/libc -I$(F)/drivers -I$(F)/services -I$(F)/player -I$(F)/ui -I$(F)/theme
all: devsim

SRCS = ap_ui_host.c ipc_b_target_host.c hw.c main.c \
  $(F)/startup/neon_fx.c \
  $(F)/ui/ui.c $(F)/ui/settings_schema.c $(F)/ui/settings_view.c $(wildcard $(F)/ui/screens/*.c) \
  $(F)/drivers/display.c psim.o $(F)/drivers/panel_init_rknanoc.c $(F)/drivers/font.c $(F)/drivers/font8x8.c $(F)/drivers/battery.c \
  $(F)/audio/audio_output.c $(F)/audio/ao_rate_table.c \
  $(F)/services/settings.c $(F)/services/settings_store.c $(F)/services/resume.c $(F)/services/audio_scope.c \
  $(F)/services/eq_profile.c $(F)/services/bt_proto.c $(F)/services/file_io.c $(F)/services/jack_sense.c \
  $(F)/services/usb_dac_sink.c $(F)/services/library_extras.c $(F)/services/bt_store.c $(F)/services/bt_link.c \
  $(F)/services/power_save.c log_host.c $(F)/services/input.c $(F)/services/scratch.c \
  $(F)/services/workbuf.c $(F)/services/media_db.c $(F)/services/media_scan.c $(F)/services/media_query.c \
  $(F)/services/art_pack.c fsh.o $(F)/services/rechord_files.c \
  theme.o \
  $(F)/player/player.c $(F)/player/bfs.c $(F)/player/playlist.c $(F)/player/codec_io.c $(F)/player/codec_io_fs.c \
  $(F)/player/tags.c $(F)/player/rg_math.c $(F)/player/codecs/codec_registry.c $(F)/player/codecs/wav.c \
  $(F)/player/codecs/mp3.c $(F)/player/codecs/flac.c $(F)/player/ringbuf.c
THEME_SRCS = $(F)/theme/theme.c $(F)/theme/theme_pkg.c $(F)/theme/theme_runtime.c $(F)/theme/theme_assets.c \
  $(F)/theme/theme_skin.c $(F)/theme/themes_builtin.c $(F)/theme/theme_file.c
theme.o: $(THEME_SRCS) $(HDRS)
	$(CC) $(CFLAGS) -Dfopen=devsim_fopen -r -nostdlib $(THEME_SRCS) -o $@

fsh.o: $(F)/services/fs_host.c $(HDRS)
	$(CC) $(CFLAGS) -include dirent.h -include sys/stat.h -Dfs_read=fsh_read -Dfs_open_read=fsh_open_read -c $< -o $@

psim.o: $(F)/drivers/panel_io_sim.c $(HDRS)
	$(CC) $(CFLAGS) -Dpanel_io_delay_ms=psim_delay -Dkeys_adc=psim_keys_adc -Dkeys_power=psim_keys_power -Dadc_read_channel=psim_adc -Dkeys_scan_tick=psim_kst -Dkeys_scan_take=psim_kstake -Dkeys_scan_failed=psim_ksf -Dboard_power_off=psim_off -Dbacklight_on=psim_blon -Dbacklight_off=psim_bloff -Dbacklight_set_level=psim_bll -Dpanel_io_send_pixel=psim_send_pixel -c $< -o $@

HDRS := $(shell find $(F) -name "*.h" -not -path "*/tests/*")
devsim: $(HDRS) $(filter-out ap_ui_host.c ipc_b_target_host.c log_host.c,$(SRCS)) gen.sh devsim.h $(F)/startup/ap_ui.c $(F)/player/ipc_b_target.c $(F)/services/log.c
	F=$(F) sh gen.sh
	$(CC) $(CFLAGS) -include dirent.h -include sys/stat.h $(filter-out %.h,$(filter-out psim.o theme.o fsh.o,$(SRCS))) psim.o theme.o fsh.o -o $@ -ldl -lm
