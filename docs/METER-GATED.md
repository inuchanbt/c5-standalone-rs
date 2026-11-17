# v0.1.8 experimental completion-gated raw acquisition

v0.1.7 physically observed DIAG_ALRT `0003` / `0001` transitions with ALATCH=0
and MEMSTAT=1. Its two complete internal-Flash readbacks and preservation audit
passed. v0.1.8 uses that evidence to test a bounded automatic clear/set gate.
**The new sampler has not yet been physically tested. GUI readings remain
unavailable; MAX, history and energy do not consume its cache.**

The [TI INA228 data sheet](https://www.ti.com/lit/ds/symlink/ina228.pdf), sections
7.3.4 and 7.6.1.12, describes conversion completion and read-to-clear behavior.
The general description and ALATCH-specific register wording differ, so this
driver explicitly requires an observed zero followed by an observed one rather
than assuming that reading a one has cleared the flag. An acquisition counter
alone is insufficient. This gate is experimental pending repeated hardware
observation. Even a successful gate does not imply simultaneous voltage/current
conversions, an exact ADC timestamp or calibrated analog accuracy.

## Acquisition and bounds

The owner starts acquisition explicitly over USB. Boot and ordinary GUI status
do not access the sensor. Each foreground step executes at most one bounded
register read outside LCD scanout:

1. Verify INA228 manufacturer/device IDs, then CONFIG/ADC_CONFIG `0000/FB68`.
2. Read DIAG_ALRT until CNVRF=0 is actually observed. Ignore an initial/repeated
   one. Require MEMSTAT=1, ALATCH=0 and no other flags, matching observed words.
3. Read until CNVRF=1 is observed after that zero. Record both observation ticks.
4. Read packed shunt/bus values; re-read CONFIG/ADC_CONFIG to reject a change.
5. Publish one complete raw cache, retaining its associated clear/set ticks.

Limits: 12 ms per register, 500 ms each for observing clear and set, 75 ms for
the shunt/bus read span, 150 ms from ready observation through publication,
1,200 ms for the complete configuration bracket, and at least 200 ms idle after
publication. A cache is current for at most 500 ms. Without host keepalive for
more than 2,000 ms, acquisition stops. Tick differences handle 32-bit wrap.

Failure is sticky, with no retry or partial publication. Old raw bytes remain
inspectable but are never current after a fault. Unsupported DIAG words stop
with error 12; gate/window expiry uses 11. This does not diagnose sensor absence.
The original raw shadow sampler, one-shot flag probe and external-storage
diagnostics remain available, but conflicting operations are refused while this
gate owns the bus. Only one sampler may run at once.

The new sensor-only callback halves the existing software delay spin count so
that successive status reads can observe the interval between conversions.
The released-line waveform and timeout/loop bounds remain unchanged. Actual bus
frequency/rise times have not been measured; no specific I2C frequency is claimed.
Ordinary raw/ID/status probes and external storage retain their tested delay.
Any failure stops and releases both lines; there is no automatic bus recovery.
No sensor configuration/calibration/value, external-storage-value or Flash
writes are implemented. DIAG reads intentionally may clear status flags.

## Host evidence

USB magic `C5N1`, command pairs `A0/A1` start, `A2/A3` status, `A4/A5` stop,
`A6/A7` gate evidence. All echo sequence/nonce and use the existing packet checks.
The status includes cache sequence/completion tick/age, raw values, configuration
and timing. A separate RAM-only evidence reply includes the publication sequence,
its clear/set observation ticks and cumulative flag counters. The collector
associates the two replies only when their publication sequences match; an
intervening publication stays recorded as unassociated rather than being hidden.
The completion tick belongs to register acquisition, not ADC sampling time.

```powershell
cd D:\c5_standalone_rs
.\gated-monitor.ps1 --seconds 20
```

The collector preserves raw HID traffic, status, gate evidence and GUI/guard
telemetry under a unique ignored capture directory. It verifies OFF on exit.
At least three different current caches with associated gate evidence are
required for collector success. `freshness_qualified` remains false: successful
collection is a physical gate observation, not full driver qualification.

Host tests execute the production C state machine for stuck-high/low flags,
bad memory/latch status, NACK/deadlines, configuration change, delayed data,
reserved bits, stale cache, lease/restart, LCD exclusion and tick wrap. Wire
tests reject stale/corrupt replies, false gate/current claims and missing or
out-of-window evidence. These software checks cannot prove physical ADC timing,
bus signal quality, GUI responsiveness or peak stack usage.

## Initial physical sequence

Keep the main measurement path disconnected and ASD LOAD OFF. Install the
concrete package using the official WITRN tool, close the tool and normal-boot
with side HID only. Run one 20-second gated monitor and check progression,
clear/set evidence, fault state, actual timings, frames, buttons and guard.
Stop on the first failure and retain the complete diagnostic record. Then
perform the full dual DFU installation/preservation audit. Only after this
step should load comparisons and calibrated GUI integration proceed.

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
