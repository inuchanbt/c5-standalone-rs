# GUI candidate hardware follow-up — 2026-11-17

Current outcome: v0.1.9 Overview values/MAX, missing main values after STOP,
retained MAX and full dual-Flash audit are confirmed on the owner's C5.
See [STATUS.md](STATUS.md) and [METER-DISPLAY.md](METER-DISPLAY.md).
Sections below preserve earlier observations; pending fields and connection
states refer to those earlier stages, not the current milestone.

## v0.1.6 physical completion and v0.1.7 flag experiment — 2026-11-17

v0.1.6 completed HID-only shadow timing, host-lease expiry, 5 V / 0.1 and 1 A
ASD/CY comparisons and full dual Flash preservation audit. Aggregate report:
`build/gui-v0.1.6-meter-shadow/hardware-validation-20261117.json`. Two 1 MiB
reads match SHA-256 `108ded61affe56db7ae1c5e9bf91b13d29c2bef5ad5c1771779694da92adb092`.
The energized-zero combined run remains incomplete because CY stopped responding;
six ASD/C5 pairs and both stop states are preserved separately. Owner reports
similar prior intermittent CY failures. USB reset recovered 1,975 scope samples
in a 2-second START/acquire/STOP/export check. No C5 firmware fault occurred.

The next untested candidate v0.1.7 adds an explicit DIAG_ALRT experiment;
see [READY-FLAG-PROBE.md](READY-FLAG-PROBE.md). Fifty-five Python tests, strict ARM
link and static layout checks passed. It reads eight raw flag words after model/
configuration gating; reads may clear latched flags, with no sensor-value or
Flash writes. GUI measurements remain unavailable. Raw 90,926 bytes; RAM 72,544;
reserved stack 8,192 and extra guard 9,376. Existing Rust GUI inputs are unchanged.

## Latest development: automated bench and v0.1.6 shadow candidate

The owner's v0.1.5 completed automated ASD/C5/CY comparisons at 5 V / 0.1, 0.5,
1 A, plus an energized 0 A point. All sessions verified LOAD OFF and healthy
GUI/guard. See [BENCH-AUTOMATION.md](BENCH-AUTOMATION.md) for exact conditions,
metadata limits and preserved failures. It remains the installed firmware.

v0.1.6 is an untested raw shadow-acquisition candidate. Forty-four Python tests
and strict ARM link passed; existing Rust GUI inputs are unchanged. Static RAM
72,544 bytes, reserved stack 8,192 bytes, extra guard 9,376 bytes. Initialization
local static estimate remains 456 bytes; estimates are not whole-call-tree or
physical peak stack measurements. No sensor/storage-value writes or ADC-ready
flag reads, and no GUI measurement updates. See [METER-SAMPLING.md](METER-SAMPLING.md).
Physical test and full installation audit of v0.1.6 remain pending.

## v0.1.5 physical validation completed — 2026-11-17

The owner installed v0.1.5 with the official tool and normal-booted with only
side HID connected. External storage was read as 128 fixed 16-byte blocks in
ascending order, then independently in descending order using a fresh nonce.
Both 2 KiB files are identical, SHA-256
`01a64410e4f9d146ee7e4215dfd60ba60c8a4a9716c997178fa000719cfbfb6c`.
All four stock settings checksums match. The first 384 bytes also match the
retained v0.1.4 partial capture. There is no complete external baseline from
before v0.1.4; equality of the new pair does not prove historical preservation
of every external byte. Full bytes/trace/decoded fields remain private under
`build/private-storage/read-20261117-122246`.

Storage blocks took 11..12 ms each. During the 6,026 ms capture the GUI completed
57 frames; before/after error stayed 0 and the sentinel guard stayed 9,448
bytes. Maximum button polling gap rose from 19 to 24 ms. Five subsequent raw
snapshots also succeeded (29..30 ms each), with error 0 and maximum polling gap
44 ms. Then 30 telemetry samples over 29.098 s showed 292 completed frames
(about 10.04 fps), LCD transfer 37 ms, error 0 and guard 9,448 bytes throughout.
This supports the LCD/I2C scheduling repair on this unit for this workload;
it is not a peak stack measurement or a production sampling qualification.

The owner entered DFU, and two full 1 MiB internal-Flash reads were identical:
`8cb7ffdee45c318e94431d1e71f1853d70b4af5941b301d9811a515c69645ebe`.
The activated application matches the v0.1.5 package. Boot/factory header,
erase tail and bytes beyond the application erase range pass preservation
checks against the qualified baseline. Audit evidence:
`build/gui-v0.1.5-cal-read/captures/dfu-20261117-122611/audit.json`.
Aggregate physical evidence is `build/gui-v0.1.5-cal-read/hardware-validation-20261117.json`;
raw log `build/captures/meter-id-20261117-122323.json`, monitor log
`build/captures/gui-20261117-122329.jsonl`. Build manifests retain their original
build-time hardware flags; this dated report records the later physical result.
The device currently remains in DFU; no HID client is running. No calibrated
GUI measurements, sensor/storage-value writes or PD controls are enabled.

## Current results

The owner installed v0.1.1, confirmed that the physical Back / Left(-) / OK /
Right(+) assignments are correct, and requested monitoring. The 30 samples in
`build/captures/gui-20261117-103058.jsonl` all report GUI/error 0: 291 completed
frames in about 29.1 seconds, LCD 37 ms, intact guard 9,472 bytes, max polling
gap 20 ms. This capture is page 0, normal orientation, 95% brightness, no sampled
key press; it does not independently test every page, rotation or visible intensity.

The owner then entered DFU. Both complete 1 MiB reads in
`build/gui-v0.1.1/captures/dfu-20261117-103322/dual-read` match SHA-256
`b738cc56813da2e7c3f3e91ed52078d112b72869c801e1e5df89b665774ba8c4`.
The installed application matches the expected activated v0.1.1 package, the
boot/factory header matches the qualified baseline, the erase tail is FF, and
all bytes after the erase range match. The saved `audit.json` passed all checks;
the two reads were independently reopened/rehashed. This audits internal Flash,
not external storage or exact peak stack use.

The owner subsequently installed v0.1.2 meter-ID and booted normally. The explicit
probe in `build/captures/meter-id-20261117-105554.json` read `0x5449` at register
`0x3E` and `0x2281` at `0x3F`, identifying INA228 at I2C address `0x40` in 6 ms.
Before/after GUI state was GUI/error 0, guard 9,472 bytes; max polling gap changed
10 to 11 ms. This is actual device evidence of the ID transaction, not a full
measurement/calibration qualification. v0.1.2 full readback remains pending.

The owner then installed v0.1.3 meter-raw and booted normally. With only side
HID connected, five raw snapshots in `build/captures/meter-id-20261117-110808.json`
succeeded in 30 ms each. CONFIG/ADC_CONFIG were `0000/FB68`; bus and shunt codes
were near zero. GUI/error remained GUI/0, guard 9,472 bytes; maximum polling gap
changed from 19 to 49 ms during explicit raw probes. See METER-INVESTIGATION.md
for raw fields and uncalibrated diagnostic analysis. v0.1.3 full readback passed at
`build/gui-v0.1.3-meter-raw/captures/dfu-20261117-115056`. The following v0.1 sections are history.

## Installation and identity

The owner reported installing `build/C5-standalone-GUI-v0.1.c4ser` with the
official updater and reconnecting normally. The package supplied for this trial
has SHA-256
`70f9045b16e96866541f3a3e7c27014c6ba008557802c091b2aa54b952f87e61`.
The assistant did not perform the installation. Until full readback, installed
image identity is based on the owner's report and GUI protocol response.

Host-access HID enumeration at 09:54 JST detected one device, VID/PID
`0716:5053`, serial `20211222`, matching the existing owner-device guard.
Sandbox enumeration returned zero; that observation was an access-context
limitation and cannot establish physical absence. No DFU or programming commands
were sent during enumeration or GUI monitoring.

## Initial-page telemetry

Evidence: `build/captures/gui-20261117-095412.jsonl`, 30 samples over about
29.1 seconds, device uptime 48,285..77,385 ms.

| Observation | Result |
| --- | --- |
| State / error | GUI / 0 for all samples |
| Completed LCD frames | 480 to 771, approximately 10/s |
| LCD transfer time | 37 ms |
| Reported core clock | 192,000,000 Hz |
| Maximum button polling gap | 10 ms |
| Intact sentinel guard | 9,472 bytes throughout |
| Pages / keys sampled | Page 0 / no key pressed |
| Display settings sampled | 60% brightness / normal orientation |

This demonstrates that the GUI foreground loop, LCD completion counter and USB
telemetry run on one physical C5. It does not independently prove visible LCD
appearance, all pages, button mapping, brightness or rotation. The monitor
samples key state once per second and may miss short taps. The sentinel covers
the extra guard below the reserved 8 KiB stack; it does not measure exact stack
peak or cover every future call path.

## Remaining checks

- Owner confirms corrected v0.1.1 button mapping; other visual checks remain scoped
  to the observations above.
- v0.1.1 dual DFU readback/preservation audit passed; later versions need their own audit.
- Measurement/ADC/PD/legacy-protocol hardware qualification: not implemented.

Finish the page/key/brightness/rotation checks while normally booted, close the
monitor/updater, manually enter DFU with OK held, and run `verify.ps1 --dfu` with
host device access. This audit only reads Flash and never installs or restores
firmware. Retain both complete reads privately; they may contain device-specific
factory/calibration data.

## Owner-reported button defect and v0.1.1 correction

The owner reports a physical row of Back / Left(-) / OK / Right(+), whereas v0.1
performs Left / Right / OK / Back at those positions. Correlating those actions
with the old native decoder yields:

| Physical button | Active-low pin | v0.1 action | v0.1.1 action |
| --- | --- | --- | --- |
| Back | PB14 | Left | Back |
| Left(-) | PB15 | Right | Left |
| OK | PA13 | OK | OK |
| Right(+) | PA14 | Back | Right |

The correction changes the C5 GPIO decoder, without changing upstream navigation
or rendering. Rotation still exchanges only the Left/Right logical bits in the
Rust adapter. A host test compiles and executes the real C GPIO decoder across
all 16 button combinations and unrelated-pin states. Existing Rust tests cover
navigation and rotation behavior. These tests validate the software mapping,
not the physical behavior of the newly built image.

The owner accepted the corrected v0.1.1 mapping and its full readback passed.
The current default `verify.ps1 --dfu` target is v0.1.5 cal-read.

## Historical v0.1.4 failure and pre-validation v0.1.5 status

With only HID connected, the first 24 external blocks were read successfully.
Continuous requests then caused LCD timeout/error 1; guard remained 9,472 bytes.
Partial private evidence is retained and marked incomplete. v0.1.5 defers I2C
work outside LCD scanout; 28 Python and six Rust tests and ARM/package checks
passed, but physical recovery/read validation is still pending. The current
device remains v0.1.4 in the recoverable GUI error loop until the owner enters
DFU. See METER-INVESTIGATION.md for evidence and limits.

## v0.1.4 full internal-Flash audit — 2026-11-17

The owner entered DFU after the recoverable GUI error. Two independent full
1,048,576-byte reads were identical, SHA-256:
`01efbb53d402334f7c51e1453f15754a0a4e394485c2c64a55d3fa4947aca84d`.
The activated application matches the v0.1.4 package; boot/factory header,
erase tail and bytes beyond the application erase range pass preservation
checks against the qualified owner baseline. Evidence:
`build/gui-v0.1.4-cal-read/captures/dfu-20261117-121753/audit.json`.
The audit used v0.1.4's pinned source snapshot and explicit build directory;
no programming command was implemented or sent. This internal-Flash audit
does not complete the partial external-storage backup. The owner has now
been asked to install v0.1.5 and normal-boot with only HID attached.

## v0.1.7 first physical flag observation — 2026-11-17

The owner installed v0.1.7 and normal-booted with side HID only. Five explicit
probes / 40 DIAG_ALRT reads succeeded. Values were `0003` 36 times and `0001`
four times. Fourth group `3,1,3,1,3,1,3,1` contains clear/set transitions with
MEMSTAT healthy and ALATCH clear. Each group took 38 ms. GUI error stayed 0,
guard 9,376 bytes; max polling gap rose 19->58 ms. LCD stayed 37 ms and advanced
23 frames in 2,301 ms. Evidence:
`build/captures/fresh-20261117-143140-149868`, aggregate
`build/gui-v0.1.7-ready-flag/hardware-validation-hid-20261117.json`.

This supports investigating an explicit observed clear->set gate. It does not
qualify every ADC sample, same-cycle atomicity, calibration accuracy or a
production sampling scheduler. No GUI measurements are enabled. Full v0.1.7
DFU installation/preservation audit is the next step; earlier offline-only
candidate descriptions record build-time status.

## v0.1.7 full internal-Flash audit — 2026-11-17

After the owner entered DFU, two complete 1 MiB readbacks matched. SHA-256
`5f2ae4ecfeccf9dc28f7953e6351756b203238c29c77a74e245c183da87113f1`. The activated application matches
the v0.1.7 package; boot/factory header, erased tail and bytes beyond the app
erase range pass the qualified baseline audit. Evidence: `build/gui-v0.1.7-ready-flag/captures/dfu-20261117-144317`.
This internal-Flash audit does not repeat the earlier external 2 KiB capture.
C5 remains in DFU, main path disconnected.

## v0.1.8 first HID-only gated run — 2026-11-17

The owner installed v0.1.8 and normal-booted with side HID only. One 20-second
run completed 75 distinct raw caches; all sequences 1..75 were observed with
matching clear/set evidence. Final counters: 246 DIAG reads, 75 clear events,
75 ready events. Acquisition intervals 237..288 ms, gate waits 10..59 ms,
clear-to-set observation spans 2..50 ms, ready-to-publication 20..68 ms,
shunt/bus read spans 7..54 ms and complete cycles 37..88 ms. Maximum register
transaction was 2 ms. These are MCU observation times, not ADC timestamps.

GUI error stayed 0, guard 9,272 bytes, LCD transfer 37 ms. GUI advanced 201
frames in 20,030 ms; maximum button polling gap rose 20->21 ms. Explicit stop
returned OFF with cache-current false; host client closed. No sensor/storage
value or Flash writes. DIAG read-to-clear side effects remain intentional.

Evidence: `build/captures/gated-20261117-150720-243831`; aggregate:
`build/gui-v0.1.8-meter-gated/hardware-validation-hid-20261117.json`.
This is one unloaded run, not analog accuracy, same-cycle V/I atomicity, bus
waveform or loaded-driver qualification. GUI/MAX/history/energy remain disabled.
Full v0.1.8 dual internal-Flash audit is pending. Earlier untested descriptions
record the candidate's build-time state.

## v0.1.8 full internal-Flash audit — 2026-11-17

After owner-confirmed DFU, two complete 1 MiB images matched SHA-256
`b89998be59ffc45909526321512300e0ba4340443f00ec763c187184cbb67115`.
The installed app matches the activated v0.1.8 package. Boot/factory header,
erased tail and all bytes beyond the application erase range pass the qualified
baseline audit. The verifier checked and used the frozen v0.1.8 source tree.
Evidence: `build/gui-v0.1.8-meter-gated/captures/dfu-20261117-150947`.
Aggregate: `build/gui-v0.1.8-meter-gated/hardware-validation-20261117.json`.
This internal-Flash check does not repeat the external 2 KiB storage capture.
Loaded acquisition and calibrated GUI integration remain pending.

## v0.1.9 first HID-only display observation — 2026-11-17

Owner installed v0.1.9 and normal-booted with side HID only. The 20-second
collector succeeded: 191 RAM telemetry rows, all settings READY, live-valid,
autonomous-enabled and error-free. All 75 sequences 75..149 were observed.
Voltage was 0..4 mV and signed current 0..2 mA; these are converted device
telemetry, not a visual reading or a calibration reference. Cache age 0..277 ms.
GUI advanced 201 frames in 20,083 ms, error 0, guard 8,928 throughout, LCD
36..37 ms and cumulative maximum button polling gap 31 ms before and after.
The cumulative gap includes startup; the collector did not time each startup
block directly. Settings READY evidences runtime acceptance, not a new full
external-storage backup.

Explicit STOP returned gated OFF. After the collector's 100 ms wait, display
telemetry reported autonomous-enabled false and live-valid false without a
conversion error. This confirms RAM invalidation; panel pixels and MAX values
still need owner observation. Legacy gated STOP parsing carries a historical
`gui_measurement_updates=false` label; v0.1.9 A8 display telemetry is the relevant
GUI data source and the raw-only label must not be used to infer no display.

Evidence: `build/captures/display-20261117-154353-282929`;
aggregate `build/gui-v0.1.9-meter-display/hardware-validation-hid-20261117.json`.
Full dual internal-Flash auditing and loaded GUI comparison remain pending.
C5 is normal-booted, main path disconnected, sampler stopped, clients closed.

A host-only `--display` bench mode now requires matching raw/gate/GUI acquisition
sequences and valid display telemetry. It aborts invalid data or unmatched
association after three attempts, and verifies missing display after STOP.
Four new injected checks plus fourteen existing bench checks pass. This host
extension does not alter v0.1.9 firmware or its frozen build sources.

## v0.1.9 loaded display telemetry — 2026-11-17

Owner normal-rebooted and restored Framework -> Sumitomo 1.0 m -> CY4500-EPR
-> C5 -> ASD-PD31, C5 PD OFF and ASD LOAD OFF. Fixed-5 V / 0.1 A acquisition
completed with ten paired records, each matching raw/gate/GUI sequence. All ten
on-device display conversions exactly match the independently reconstructed
stock/settings model after mV/mA rounding. Device telemetry: 5,071..5,081 mV,
-101..-103 mA. Signed current is retained; the upstream panel renderer uses
magnitude plus direction. The offline unrounded current magnitude averaged
0.101685606 A vs ASD 0.100000 A, difference +1.685606 mA. No correction was fitted;
this is a limited comparison across different path positions and bracket times.

GUI error 0, guard 8,928 bytes; 223 frames / 22,306 ms, LCD 36..37 ms, cumulative
max button gap 22 ms. CY captured 22,280 scope samples and completed STOP/export;
all decoded requests were Fixed 5 V. ASD LOAD OFF verified. Gated STOP returned
OFF; subsequent display telemetry was invalid and autonomous renewal disabled.
Panel pixels and MAX behavior still need owner observation. Full dual v0.1.9
Flash audit remains pending. Historical gated-parser gui_measurement_updates
false is not applicable to the separate v0.1.9 A8 display telemetry.

Evidence: `build/captures/bench-20261117-155448-243078`, including
`display-validation.json` and `comparison-analysis-v2.json`; aggregate:
`build/gui-v0.1.9-meter-display/loaded-validation-20261117.json`.
C5 remains normally booted, main bench wiring connected, PD OFF; ASD OFF,
C5 sampler OFF, CY stopped and all clients closed. No firmware was changed.

## v0.1.9 full internal-Flash audit and visual status — 2026-11-17

Owner explicitly reported not watching the panel during the earlier load/stop
trial; visual readings and MAX behavior remain unconfirmed. After disconnecting
the main path and entering DFU, two complete 1 MiB Flash reads matched SHA-256
`dc07f64d9a0da4a32adce5f2463028dec939140d59c1f01373faf57a70569e64`.
Activated v0.1.9 package matching, boot/factory header preservation, erased tail
and preservation beyond the application erase range all pass. The verifier
validated and used the frozen v0.1.9 source snapshot. This internal audit does
not repeat the external settings backup or establish full calibration accuracy.

Evidence: `build/gui-v0.1.9-meter-display/captures/dfu-20261117-155903`.
Aggregate: `build/gui-v0.1.9-meter-display/hardware-validation-20261117.json`.
C5 remains in DFU, main path disconnected; ASD OFF, CY stopped, clients closed.
The experimental Overview integration now has host, HID, loaded conversion and
installation/preservation evidence. A deliberately observed screen trial remains
before claiming panel confirmation. No further firmware update is required.

## v0.1.9 owner-ready visual trial telemetry — 2026-11-17

Owner confirmed restored wiring, LOAD OFF and readiness to watch Overview.
The fixed-5 V / 0.1 A hold ran for 20 seconds and completed 20 paired records.
All raw/gate/GUI sequences match, and every on-device mV/mA conversion equals
the offline model after rounding. Telemetry was 5,071..5,076 mV / -101..-102 mA.
GUI error stayed 0, guard 8,928, LCD 37 ms; frames advanced 326 in 32,687 ms
including setup/teardown. Cumulative max button polling gap remained 31 ms.
ASD LOAD OFF, gated OFF and display invalid/autonomous-disabled were verified.
CY captured 32,610 scope samples and completed STOP/export; requests were Fixed
5 V only. Offline current magnitude minus ASD averaged +1.588272 mA; no fitted
correction or general calibration claim.

Evidence: `build/captures/bench-20261117-160326-749737`, including
`display-validation.json` and `comparison-analysis-v2.json`. This capture is
telemetry for an owner-ready observation trial; readiness does not establish
what the owner actually saw. An explicit question about visible readings/MAX,
missing main values after STOP and retained MAX is pending.
C5 is normal, PD OFF, bench wiring connected; ASD OFF, C5 sampler OFF, CY stopped,
host clients closed. No firmware changes since the successful full Flash audit.

## v0.1.9 panel confirmation completed — 2026-11-17

After the owner-ready 20-second trial, the owner explicitly confirmed visible
readings/MAX, main fields returning to dashes after STOP, and retained MAX.
Four original photographs were copied byte-for-byte into the ignored build
visual-evidence folder with SHA-256 hashes. Photo 3 shows 5.07 V / 0.10 A /
0.51 W and MAX 5.10 V / 0.10 A / 0.52 W; photo 4 shows missing main readings
with those MAX values retained and the METER WAIT footer. Photos 1/2 show
near-zero and energized near-zero-current states. They are actual panel evidence,
not host renders or an independent accuracy reference.

Evidence: `build/gui-v0.1.9-meter-display/owner-visual-20261117/manifest.json`.
Current aggregate: `build/gui-v0.1.9-meter-display/overview-milestone-20261117.json`.
The first experimental Overview V/I/power/MAX connection now has host, matched
live telemetry, load, panel and full internal-Flash preservation evidence on the
owner unit. Earlier stage reports retain their original pending fields; the
current aggregate supersedes them. No new firmware or hardware command was sent
while recording this confirmation. Firmware remains experimentally bounded to
0..5.5 V / |I| <=1.1 A; history/energy, line/ripple ADC, PD and broader calibration
are still unfinished. The last verified bench state is LOAD OFF, sampler OFF,
CY stopped, normal C5 boot and all host clients closed.
