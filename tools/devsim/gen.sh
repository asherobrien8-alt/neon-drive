#!/bin/sh
# hostify ap_ui.c: wfi -> host_wfi()
F=${F:-$(cd "$(dirname "$0")/../../firmware/.rechord-src/firmware" && pwd)}
sed 's/__asm__ volatile("wfi");/host_wfi();/' $F/startup/ap_ui.c > ap_ui_host.c
grep -q host_wfi ap_ui_host.c || { echo "wfi patch failed"; exit 1; }
sed -i '1i void host_wfi(void);' ap_ui_host.c
sed 's/__asm__ volatile("dmb" ::: "memory");/__sync_synchronize();/' $F/player/ipc_b_target.c > ipc_b_target_host.c
sed 's/^    append_line(line);$/    devsim_log(line);\n    append_line(line);/' $F/services/log.c > log_host.c
sed -i '1i void devsim_log(const char *line);' log_host.c
grep -q devsim_log log_host.c || exit 1
