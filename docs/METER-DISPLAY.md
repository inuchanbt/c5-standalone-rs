# v0.1.9 experimental live Overview

This candidate connects C5 readings to the existing Rust Overview renderer and
RAM-only MAX values. **The initial physical milestone is confirmed on the
owner's C5**: HID and loaded conversion, panel readings/MAX/STOP behavior and
full internal-Flash audit passed. See [STATUS.md](STATUS.md) for the current
public summary. The preceding v0.1.8
completed HID-only gating, full internal-Flash auditing and fixed-5 V comparisons
at 0, 0.1, 0.5 and 1 A. The source renderer/navigation remain upstream-pinned.

## Runtime path

After GUI initialization, the foreground reads the first 240 bytes of the
stock-addressed external settings storage twice in 16-byte blocks. Each bounded
transaction runs outside LCD scanout; the GUI/USB loop runs between blocks.
Both passes must match byte-for-byte, and all four stock XOR/A5 checksums must
match. There is no storage initialization/repair path. Only this prefix is used;
it is not a replacement for the previously captured complete 2 KiB backup.

The decoder extracts signed integer and float correction fields identified in
the stock V8.5 code. It checks finite reference values, positive bounded spans
and plausible zero correction before accepting them. Actual owner correction
values are loaded at runtime; they are never embedded in source or packages.
The conversion reproduces the existing offline model's f32/f64 rounding stages,
signed wide-range shunt input and inclusive -2..+1 mA stock deadband. It does not
reproduce the stock moving-average filter or establish calibration provenance.

After settings validation the device starts the v0.1.8 clear/set-gated sampler.
Identity and CONFIG/ADC_CONFIG must match INA228 and `0000/FB68`; every published
cache requires an observed clear followed by set, complete bounded data reads
and unchanged configuration. The foreground renews the host lease while owning
autonomous display acquisition, so the display runs without a PC. Diagnostic
STOP disables that renewal and acquisition; reboot restores autonomous startup.
A transport/settings/configuration/conversion error is sticky until reboot.
No automatic retry, sensor value writes or active C5 PD requests are added.
DIAG reads can clear status flags, including during autonomous operation.

The first candidate deliberately accepts converted 0..5.5 V and |I| <=1.1 A,
the envelope surrounding the tested 5 V bench. Values outside this envelope
stop the meter and show missing readings. This is a display bound, **not source
or load protection**; it does not change negotiated voltage or disconnect power.
PD/QC/cable controls remain unavailable. Do not use this candidate to validate
other voltage ranges. One unit and a few steady comparisons do not establish
full-range accuracy or simultaneous voltage/current conversions.

## GUI and telemetry

Overview receives millivolts and signed milliamps, rounded to nearest integer.
The unchanged renderer presents current magnitude and its direction indicator;
the sign is retained in telemetry. Power and MAX use the existing renderer's
calculation. MAX is RAM-only since boot, remains visible after readings expire,
and has no new reset/persistence control. No old/failed/partial/out-of-range
sample updates MAX. More than 500 ms after acquisition, or upon invalidation,
the main readings return to missing. Footer: `EXPERIMENTAL / PD NOT READY`,
`METER WAIT / PD NOT READY` or `METER ERROR / PD NOT READY`.

Graph/energy inputs remain unwired and their footer explicitly says so. Lines,
ripple, protocol results and other pages do not receive manufactured readings.
Unknown protocol UI is not a source-detection result; PD is still unavailable.

USB `A8/A9`, magic `C5V1`, is RAM-only display status: settings state/error,
autonomous enable, live validity, mV, signed mA, associated acquisition sequence,
cache age and conversion error. Sequence/nonce/checksums are checked by
`display-monitor.ps1 --seconds 20 --stop`. The optional stop verifies gated OFF
and missing display readings. Ordinary monitor does not stop the autonomous
meter. Earlier raw/storage diagnostics return BUSY during settings load or
gated sampling. Stop the sampler before explicit storage/raw work. Historical
shadow/gated collectors describe their older raw-only candidates; use the new
display collector to validate GUI values and runtime ownership.

## Offline validation and first physical check

The sequence below records the original build/installation plan. Later dated
observations culminate in the final panel-confirmation section; their earlier
pending states are historical, not outstanding work for this milestone.

Eleven Rust integration tests cover navigation/rendering plus conversion,
direction, checksums, invalid correction fields, range limits, stale data,
fault latching and MAX preservation. Eighty-five Python/native tests cover
the read engine, gate, dual-prefix state machine, host bench and wire formats.
Thirty-eight retained bench vectors with private settings match the prior
offline stock model after display-unit rounding. The associated preview is
rendered on the host from captured input, not a C5 photo. Firmware memory/layout
and package/source checks are recorded with the build; estimates are not
physical peak-stack measurements.

Install the prepared package with the official WITRN tool, starting with the
main measurement path disconnected and side HID only. Close the updater and
normal-boot. Verify startup settings reach READY, new GUI samples advance,
frames/keys/guard remain healthy, then test STOP removes main readings.
After reboot, repeat the fixed-5 V bench with visual/reference comparison and
record MAX behavior and signed telemetry. Finally repeat the full dual DFU
installation/preservation audit. Actual v0.1.9 hardware outcomes remain pending.

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
