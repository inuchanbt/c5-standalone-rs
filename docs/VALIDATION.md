# C5 standalone validation

## Current v0.1.9 outcome — 2026-11-17

Experimental Overview V/I/power and RAM-only MAX are confirmed on the owner
unit. Host tests, matched loaded raw/gate/GUI conversion, owner panel/STOP/MAX
observations and full dual internal-Flash installation/preservation audit passed.
The public evidence summary, tested package digest, memory figures and remaining
limits are in [STATUS.md](STATUS.md). Detailed display observations are in
[METER-DISPLAY.md](METER-DISPLAY.md).

The following sections are historical candidate-stage records. References to
"current", "next", "pending" or a device state describe the stage when written;
they do not override the current status above. Original raw evidence and frozen
build manifests remain local under ignored `build/`.

## v0.1.8 completion-gated raw candidate — 2026-11-17

v0.1.7 completed its physical flag experiment and dual internal-Flash audit.
The new v0.1.8 candidate is not installed/physically tested. Seventy-five Python
checks and strict ARM link pass. It requires an observed CNVRF clear->set before
each raw data read sequence, bounds all waits and rejects partial/stale/faulted
publication. New sensor-only half-spin timing remains physically unqualified;
existing ordinary diagnostics/storage timing is unchanged. No sensor/storage
value or Flash writes; DIAG reads can clear status. GUI/MAX/history/energy remain
unavailable. See [METER-GATED.md](METER-GATED.md) for protocol, deadlines and
physical sequence. Raw 92,142 bytes; static RAM 72,648; stack 8,192; extra guard
9,272. Largest syntactic local-frame estimate 856; none is a physical peak-stack
measurement. The Rust GUI inputs match those from the prior six passing tests.

The dated sections below preserve build-time and later physical observations.

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

## Current candidate: v0.1.5 deferred diagnostics — 2026-11-17

Package: `build/gui-v0.1.5-cal-read/C5-standalone-GUI-v0.1.5-cal-read.c4ser`.
SHA-256: `fec596fdcd07473f93793334c2888e6fafa0597a6a631e2ef77a7aa50dfaa6f5`.

Twenty-eight Python and six Rust tests passed; ARM link, source/upstream pins,
package round trip and a synthetic installation/preservation audit passed.
The real C queue helper is tested for request-prefix preservation, no consumption
inside scanout and single consumption outside it. A synthetic timing model
reproduces the old timeout and completes with deferred jobs. This model is not
a hardware benchmark. ID, raw and storage I2C jobs now execute outside LCD
scanout; the LCD timeout remains 250 ms. Raw image 89,350 bytes, static RAM
72,472 bytes, reserved stack 8,192 bytes and additional guard 9,448 bytes.
Largest conservative local stack estimate is 2,428 bytes. Later physical validation is recorded above; exact peak stack measurement
remains pending.

### v0.1.4 physical failure retained

The owner installed v0.1.4 and booted with HID only. Blocks 0..23 succeeded
(384 bytes), then GUI_NOT_READY. Follow-up status reported LCD timeout/error 1,
with the 9,472-byte guard intact. Continuous I2C requests executed in LCD row
service and exceeded its frame wall-time budget. This is a scheduling defect;
no storage-value writes or stock initialization were implemented. The private
partial capture remains `build/private-storage/read-20261117-115704`, marked
incomplete. Four settings checksums within the captured prefix match, but a
full independent two-pass external backup is still required. v0.1.4 package,
source snapshot and evidence are preserved. Full internal-Flash audit subsequently passed; see the dated record below.

## v0.1.3 raw diagnostics — 2026-11-17

Package: `build/gui-v0.1.3-meter-raw/C5-standalone-GUI-v0.1.3-meter-raw.c4ser`.
SHA-256: `22cef1285ee090474931959fba659cc5304c45500f276008c9f6450fc48746db`.

Eighteen Python tests passed, including real native ID/2-byte/3-byte read
transactions, outgoing read-only waveform checks, unknown/wrong IDs, exact NACK
stages, stuck bus/clock/deadline cleanup and corrupt/stale/incomplete wire data.
Six Rust GUI tests passed with unchanged Rust inputs. ARM link, upstream/input
hashes, package round trip and synthetic preservation audit passed.

The owner installed v0.1.3 and normal-booted it. Five actual HID-only raw
snapshots succeeded, each taking 30 ms. CONFIG/ADC_CONFIG were `0000/FB68`;
bus and shunt codes were near zero. GUI state/error stayed GUI/0 with intact
9,472-byte guard; maximum polling gap rose from 19 to 49 ms during the explicit
diagnostics. This is not calibration, reference accuracy or a complete ADC
freshness/coherency qualification. Detailed data and evidence paths are in
[METER-INVESTIGATION.md](METER-INVESTIGATION.md).

Raw image 88,558 bytes; text/read-only data 84,462 bytes; static RAM 72,448 bytes;
reserved stack 8,192 bytes; additional guard 9,472 bytes; largest conservative
local stack estimate 2,428 bytes across 598 disassembled functions. The full
v0.1.3 dual readback passed at `captures/dfu-20261117-115056` under its build directory. The build manifest's false hardware
flags describe build-time status; later physical observations are separate.

## v0.1.2 ID-only diagnostic — 2026-11-17

Package hash `4478395d9680968b1e2683b012a43f0ac7f0522a3a9092efbcb351592ffb0729`.
The real ID request identified INA228 (`0x5449/0x2281`) at `0x40` in 6 ms,
GUI error 0 and guard 9,472 bytes before/after. Evidence:
`build/captures/meter-id-20261117-105554.json`. Offline tests included 15 Python
and six Rust GUI tests; strict ARM link and package/preservation model passed.
This version has no full installation readback. Its package and source snapshot
remain under `build/gui-v0.1.2-meter-id`.

## v0.1.1 button correction — 2026-11-17

Package: `build/gui-v0.1.1/C5-standalone-GUI-v0.1.1.c4ser`.

SHA-256: `9856b468680d3d776c262161242f1a64c0a566b693581ba64bba1d2b57fdfe11`.

The owner reported that the physical row Back / Left(-) / OK / Right(+)
performed Left / Right / OK / Back in v0.1. The native GPIO decoder now maps
PB14 to Back, PB15 to Left, PA13 to OK, PA14 to Right. Upstream drawing and
navigation, and the Rust layer's Left/Right exchange on rotation, are unchanged.

Passed offline for v0.1.1:

- Six Rust integration tests, including navigation and rotation controls.
- Eight Python tests, including a new test that compiles/executes the actual
  native GPIO decoder for all 16 key combinations with two unrelated-pin states.
- ARM link, upstream source pins, build input hashes and static stack checks.
- Package round trip and synthetic installation/preservation audit against the
  same qualified owner baseline. This is not a physical full readback.
- The original v0.1 package remains byte-identical at its old build path.

New build: raw image 86,710 bytes; text/read-only data 82,614 bytes; static RAM
72,448 bytes; reserved stack 8,192 bytes; guard 9,472 bytes; largest conservative
local stack estimate 2,428 bytes across 588 functions. Exact peak stack use has
not been measured. Evidence is under `build/gui-v0.1.1`, including `manifest.json`,
`source-hashes.json`, `stack-estimates.json` and `offline-validation.json`.

The owner installed v0.1.1 and confirmed correct button assignments. Its
30-second GUI telemetry and full dual DFU readback/preservation audit passed.
Both 1 MiB reads have SHA-256
`b738cc56813da2e7c3f3e91ed52078d112b72869c801e1e5df89b665774ba8c4`.
Evidence: `build/gui-v0.1.1/hardware-validation-20261117.json`. Other visual
observations and exact peak stack use remain limited as recorded there.

## Historical candidate: v0.1

Candidate: `C5-standalone-GUI-v0.1.c4ser`.

SHA-256: `70f9045b16e96866541f3a3e7c27014c6ba008557802c091b2aa54b952f87e61`.

## Passed offline

- Six Rust integration tests: real button navigation across groups and monitor
  tabs; blocked charging-protocol actions including long holds; unsupported
  settings and working RAM display settings; all 17 pages in both orientations;
  complete logical-pixel coverage and exact rotation mapping; in-place startup
  matching the normal constructor's input state, history and rendered frames.
- Seven Python tests: telemetry wire layout, nonce/checksum rejection,
  package round trip and corruption rejection, invalid vectors/tags, preservation
  audit corruption rejection, oversized-stack detection and in-place-stack
  accounting/dynamic-adjustment rejection.
- ARM static link with no unresolved symbols, strict C compiler warnings,
  upstream Git-blob/patch verification and source hash checks.
- Synthetic installation audit using the actual generated package and the
  owner's previously verified baseline, including the observed activation byte.
- Host previews from the actual Rust renderer inspected for layout. No dummy
  meter values, PD offers or successful device operations are injected.

## Measured build sizes

| Item | Bytes |
| --- | ---: |
| Raw flash image | 86,934 |
| Text / read-only data | 82,838 |
| Static RAM | 72,448 |
| Logical RGB565 framebuffer | 64,800 |
| Reserved stack | 8,192 |
| Additional sentinel guard | 9,472 |
| In-place initialization local stack estimate | 456 |
| Largest conservative per-function static estimate | 2,428 |
| Official-format padded package | 917,504 |

The stack estimates cover 588 disassembled functions. They sum local downward
SP adjustments; they do not bound a whole call chain or interrupt nesting.
An earlier whole-struct startup copy exceeded the stack budget and was removed
before producing this candidate. The history constructor patch leaves default
contents and runtime history behavior unchanged.

## Physical follow-up — 2026-11-17

The owner reported installing the GUI package and reconnecting normally. A host
HID enumeration then detected the previously qualified owner C5. A 30-second
read-only monitor run returned `state=GUI`, `error=0`, approximately 10 completed
LCD frames/s, 37 ms LCD transfer, 192 MHz reported core clock, 10 ms maximum
button polling gap, and 9,472 bytes of intact sentinel guard across 30 samples.
The captured uptime range was 48,285..77,385 ms. This log covers only page 0,
no keys, 60% brightness and normal orientation; it does not validate the other
pages or controls. The sentinel is not a measurement of exact stack peak.

See `build/captures/gui-20261117-095412.jsonl` and
[HARDWARE-VALIDATION.md](HARDWARE-VALIDATION.md). The original build manifest's
`hardware_tested=false` describes the candidate at build time; it is retained
unchanged as historical evidence. New observations are recorded separately.

Sandbox HID enumeration returned zero devices, whereas enumeration with host
access detected one device and telemetry worked. A zero result inside the
sandbox must not be treated as proof that the physical C5 is disconnected.

## Relocated offline validation — 2026-11-17

Six Rust integration tests and seven Python tests passed again under
`D:/c5_standalone_rs`. All 18 regenerated PPM page/settings previews matched the
imported originals byte-for-byte. Upstream pins, build input hashes, package
round trip and the synthetic installation audit passed again.

ARM compilation/link and static stack checks passed using the C5-local Cargo
cache. This rebuilt raw image is 86,694 bytes and its package SHA-256 is
`0d2bfaa8933766d76c6d9a958813aa46ff2a75c58d718ce96b8c6aa068aecc01`.
It differs from the imported candidate; both binaries contain dependency source
paths, now pointing to different cache locations. Binary identity or hardware
equivalence of this rebuild has not been established. Rebuilt outputs are kept
under `build/relocated-rebuild-20261117`; the original candidate and matching
build evidence were restored to their original `build/` paths. The build sizes
above and the package hash at the top continue to describe the original.

## Still unverified

The assistant did not flash the C5; installation and normal startup were reported
by the owner. USB GUI response and initial-page timing/guard are now observed.
Visual geometry/color/scanout, all-page/four-key behavior, brightness, rotation,
actual stack peak and full installation readback still require separate evidence.

The C5 sensing IC, measurement calibration/transport, line ADC and PD PHY have
not been established. This image cannot measure power or negotiate charging.
Offline GUI results must not be described as a completed functional meter port.

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

## v0.1.8 loaded attempt blocked by CY readiness — 2026-11-17

Owner confirmed normal boot, restored Framework/Sumitomo/CY/C5/ASD wiring,
C5 PD OFF and ASD LOAD OFF. Attempt `bench-20261117-151611-161685` aborted
before ASD CLI load control or C5 sampler start: CY did not provide any scope
samples within 10 seconds. One USB read and zero PD/scope records were observed.
Console also printed its generic interface-claim/use error. That message does
not establish another application owning the interface or the root cause.
No matching Analyzer-named process was observed in the process-name check.
The original incomplete manifest/empty captures are retained; no automatic retry.

Follow-up owner-identity/status queries found ASD output ON at 5.085 V / 0 A,
contrary to the reported OFF condition. A separate LOAD OFF command was sent,
and a CRC-valid status confirmed output OFF, 0 V / 0 A. No 0.1 A load command
was sent in this attempt. C5 gated status was OFF, GUI error 0, guard 9,272,
LCD 37 ms and maximum button polling gap 20 ms. Follow-up evidence remains in
`followup-status.json`, `followup-load-off.json` and `followup-c5-wire.jsonl`.
All host clients have closed. CY STOP success is not established by this run.

Next: owner reconnects CY PC USB; verify a short native CY START/acquire/STOP
capture before another combined attempt. Keep ASD LOAD OFF and C5 normal with
PD OFF. v0.1.8 loaded validation and calibrated GUI integration remain pending.

## v0.1.8 loaded gate validation completed — 2026-11-17

Owner reset CY PC USB and closed Utility. A 2-second native capture completed
with 1,990 scope samples and exit 0 including STOP/export. Evidence:
`build/captures/cy-recovery-20261117-151930-471`. The preceding readiness failure
remains preserved, with no claim that its underlying cause is fixed.

Four combined sessions then completed at Fixed 5 V, with C5 PD OFF and the
Framework -> Sumitomo 1.0 m -> CY4500-EPR -> C5 -> ASD-PD31 path:

| Current setting | Capture suffix | Steady / precheck pairs | C5 current magnitude mean | ASD mean | Mean difference |
| --- | --- | --- | --- | --- | --- |
| 0.1 A | 151944-804150 | 10 / 0 | 0.102171275 A | 0.09995 A | +2.221275 mA |
| 0.5 A | 152049-838349 | 10 / 1 | 0.500946656 A | 0.50000 A | +0.946656 mA |
| 1 A | 152134-678276 | 10 / 1 | 0.999635488 A | 1.00000 A | -0.364512 mA |
| 0 A energized | 152225-950120 | 6 / 0 | 0 A after stock deadband | 0 A | 0 mA |

Capture paths are `build/captures/bench-20261117-<suffix>`. Every paired C5 cache
has matching clear/set evidence. The analysis keeps precheck points separately,
retains signed current, and uses magnitude only for comparison. Reported C5
units are the offline stock-code/settings reconstruction, not current GUI
readings or a fitted calibration. Zero after deadband does not mean zero raw ADC
code. Instruments occupy different path positions and bracket times; readings
are not exactly simultaneous and do not establish full-range accuracy.

All decoded requests were Fixed 5 V. All four runs verified ASD LOAD OFF and
C5 gated OFF; CY STOP/export succeeded. GUI error remained 0 and guard 9,272
bytes throughout. CY scope counts were 22,290 / 26,285 / 26,330 / 18,225; its
absolute analog calibration remains unqualified. External CLI source hashes
still match. No C5 firmware, sensor configuration or storage-value writes.

Aggregate: `build/gui-v0.1.8-meter-gated/loaded-validation-20261117.json`.
C5 is now normal-booted with bench wiring connected, PD OFF; ASD LOAD OFF,
gated sampler OFF, CY stopped and all host clients closed. The v0.1.8 package
already passed its dual internal-Flash audit before these read-only C5 tests.
Next development is a runtime checked conversion adapter and experimental GUI
measurement path, retaining stale/fault rejection and protecting private settings.

## v0.1.9 experimental display candidate — 2026-11-17

Overview V/I/power and RAM-only MAX now consume checked runtime conversion and
complete gated samples. Eleven Rust integration tests and 85 Python/native
checks passed. All 38 private captured vectors matched the prior stock model
after mV/mA rounding. The host preview from a captured 0.1 A vector was inspected.
ARM link passed: raw 98,150 bytes, static RAM 72,992, reserved stack 8,192,
extra guard 8,928; largest local static estimate 904 bytes. Physical startup,
values/keys/guard, stop/expiry and full dual Flash audit remain pending.
See METER-DISPLAY.md; limits include 0..5.5 V / |I| <=1.1 A, no stock filter,
no atomic V/I, no full-range accuracy claim and no runtime persistent writes.

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
