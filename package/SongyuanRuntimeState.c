// SPDX-License-Identifier: MIT
// Shared counters for the SM8850 driver ABI and inert display-stage callbacks.
// No diagnostic page or observer is started by this module.
#include <stdint.h>

char native_touch_rows[4][120];
volatile uint32_t native_touch_loop_step, native_touch_seq, native_touch_count, native_touch_hid_reports;
volatile int native_touch_xs[12], native_touch_ys[12], native_touch_ids[12];
volatile unsigned native_touch_stage_req;
char native_cpufreq_row[120];
volatile uint32_t native_cpufreq_stage;
void sheng_cpufreq_poll(void) {}
void boot_log_tick(unsigned seconds) { (void)seconds; }
volatile uint32_t native_adreno_audit_attr;
volatile uint64_t native_adreno_audit_ticks;

char boot_progress_ext[8][48];
char boot_progress_ext_wide[2][112];
int boot_progress_prepare_scanout(void) { return 1; }
void boot_progress_cancel_scanout(void) {}
void boot_progress_stage(const char *stage) { (void)stage; }
int boot_progress_pulse_anchor(uintptr_t base, uint64_t bytes, unsigned w, unsigned h, unsigned stride) {
    (void)base; (void)bytes; (void)w; (void)h; (void)stride; return 0;
}
