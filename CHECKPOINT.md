# C5 standalone port checkpoint

## Publication preparation — 2026-11-17

English/Japanese READMEs now summarize the v0.1.9 experimental Overview milestone,
remaining features, source-only publication scope and completed workspace move.
Public summary: docs/STATUS.md; candidate history: docs/CHANGELOG.md. Two selected
owner panel photos are under docs/images. Private Flash/settings/captures and
the complete migrated legacy tree remain ignored under build/.
Publication host checks passed: 11 Rust integration tests, 89 Python/native
tests, renderer previews and upstream source pins. No firmware was rebuilt and
no device I/O was performed. Destination: inuchanbt/c5-standalone-rs, main.

## Latest live status — 2026-11-17

Working root D:/c5_standalone_rs. CURRENT HARDWARE: v0.1.9 normal boot,
PD OFF, full Framework/Sumitomo/CY/C5/ASD wiring restored and side HID connected.
Latest owner-ready visual trial finished; ASD LOAD OFF, C5 gated OFF/display
invalid, CY STOP/export all confirmed. All host clients closed.
Owner explicitly confirmed the repeated trial: readings/MAX visible, main values
returned to dashes after STOP, MAX retained. Four photos independently show the
loaded and stopped panel states; originals copied/hash-checked under build.

v0.1.9 first experimental Overview integration CONFIRMED: host/HID/load/panel
and full Flash audit passed. This is not a completed meter/PD firmware.
Package: build/gui-v0.1.9-meter-display/C5-standalone-GUI-v0.1.9-meter-display.c4ser
SHA-256 f05abfd3bfa141f498099c2d27dd9349c0ba49a61d34560581d0f0abcc9f830d.
Overview V/I/power and RAM-only MAX consume checked samples. Signed current
retained (upstream renderer uses magnitude/direction). History/energy/line ADC/
ripple/PD are still unavailable. No upstream renderer/navigation changes.
- Runtime first-240-byte settings read twice, block-by-block outside LCD;
  byte equality + all four stock XOR/A5 checksums + bounded finite fields.
  No private owner coefficients embedded. No storage init/repair/value writes.
- Automatic gated sampling after accepted settings, strict INA228 / 0000/FB68,
  observed clear->set and bounded complete acquisition. Runtime renews lease
  without PC. Explicit A4 STOP disables autonomous renewal; reboot restores it.
- 0..5.5 V / |I| <=1.1 A experimental display envelope. No power-path protection.
  Missing on >500 ms cache age, stop or fault. Conversion/transport errors are
  sticky until reboot. No sensor value or Flash writes; DIAG read side effects.
- Rust 11 integration tests and Python/native 85 tests passed. New Rust code
  matched all 38 private v0.1.8 bench vectors to the offline model at mV/mA.
  Host-captured-preview.png inspected; it is not a device photo.
- Raw 98,150 bytes, RAM 72,992, stack reserved 8,192, guard 8,928; largest
  syntactic local frame 904 bytes, not a physical peak-stack measurement.
- See docs/METER-DISPLAY.md and build offline-validation.json/source snapshot.

Actual HID-only evidence: build/captures/display-20261117-154353-282929.
Aggregate: build/gui-v0.1.9-meter-display/hardware-validation-hid-20261117.json.
191 rows / 75 distinct consecutive display samples (75..149), settings READY,
live valid, 0..4 mV / 0..2 mA, age 0..277 ms. GUI error 0 / guard 8,928,
201 frames / 20,083 ms, cumulative max button gap 31 ms before and after.
STOP then 100 ms wait: gated OFF, autonomous false, display invalid, no error.
This is RAM telemetry, not visual confirmation of panel/peaks. Legacy gated
parser's gui_measurement_updates=false label is obsolete for this candidate.

Loaded GUI telemetry PASSED: build/captures/bench-20261117-155448-243078.
Ten paired raw/gate/display sequences match; every on-device mV/mA equals the
independent offline model after rounding. Telemetry 5,071..5,081 mV / -101..-103
mA. Model magnitude mean .101685606 A vs ASD .100000 A; +1.685606 mA difference,
not fitted calibration or full accuracy qualification. GUI error 0, guard 8,928,
223 frames /22,306 ms, max button gap22 ms. CY22280scope/STOP/export passed,
all decoded requests Fixed5V. ASD OFF and display_stop samplerOFF/displayinvalid
confirmed. Aggregate build/gui-v0.1.9-meter-display/loaded-validation-20261117.json.

v0.1.9 full dual internal-Flash audit PASSED:
build/gui-v0.1.9-meter-display/captures/dfu-20261117-155903.
Flash SHA-256 dc07f64d9a0da4a32adce5f2463028dec939140d59c1f01373faf57a70569e64.
Activated package, boot/factory, erased tail and outside-app checks all pass.
Aggregate: build/gui-v0.1.9-meter-display/hardware-validation-20261117.json.
Historical earlier pending fields in individual stage records are preserved.

LATEST VISUAL TRIAL: build/captures/bench-20261117-160326-749737.
Owner confirmed ready to watch; 5 V /0.1 A held20s,20 paired records. All raw/
gate/display sequences and rounded conversion values match. Telemetry5071..5076mV,
-101..-102mA. GUIerror0/guard8928/LCD37/maxgap31;326frames in32687ms incl setup.
CY32610scope/STOP/export, ASD OFF, gated OFF, display invalid all confirmed.
No firmware change after completed dual Flash audit.
VISUAL CONFIRMED: owner reported readings/MAX, then main '--' with MAX retained.
Photo3:5.07V/.10A/.51W; MAX5.10V/.10A/.52W. Photo4: main dashes, same MAX.
Four original photos copied/hash-checked, no public upload:
build/gui-v0.1.9-meter-display/owner-visual-20261117/manifest.json.
Current milestone aggregate: build/gui-v0.1.9-meter-display/overview-milestone-20261117.json.
Older pending fields are historical. No more visual/DFU repeat is required for
this firmware absent a new concern. Owner task to connect acquired values to
Overview is complete within the experimental envelope. Last verified state:
normal C5/PDOFF, wiring connected; ASD OFF, sampler OFF, CY stopped/clients closed.
NEXT development milestones: history/energy integration, then line/ripple ADC,
PD receive before active control, and broader calibration/range qualification.
Do not claim those features implemented. Keep old data, backups and upstream pins.

v0.1.8 physical evidence is preserved:
- HID: build/captures/gated-20261117-150720-243831, all 75 samples matched gates,
  GUI error 0 / guard 9,272. Full Flash: captures/dfu-20261117-150947 under build
  gui-v0.1.8-meter-gated; SHA b89998be59ffc45909526321512300e0ba4340443f00ec763c187184cbb67115.
- Loaded aggregate: build/gui-v0.1.8-meter-gated/loaded-validation-20261117.json.
  5 V / 0.1,0.5,1,0 A steady pairs 10/10/10/6 plus two prechecks. Mean magnitude
  differences vs ASD +2.221275,+0.946656,-0.364512,0 mA (zero after deadband).
  All gate evidence, GUI, ASD OFF, C5 OFF and CY export pass. Private files stay
  ignored under build; coefficients not fitted. Different positions/times, not
  atomic V/I or general accuracy proof.
- Prior CY failure bench-20261117-151611-161685 is retained (0 pairs). USB reset
  recovered 1,990 scope samples in 2s, then four loaded sessions passed. Root
  cause of intermittent CY failures remains unresolved; no external edits.

2026-11-17. User requested porting `inuchanbt/kws-x1-standalone-rs`, including
its GUI, to the WITRN C5. Conversation is Japanese; development documentation
is English primary. The working root is now `D:/c5_standalone_rs`; the original
`D:/doom_on_c5/c5-standalone-rs` was fully relocated and removed at the owner's
request. A verified complete legacy copy is retained inside the active root;
see `docs/MIGRATION.md`. Do not modify the original
KWS or KM003C checkouts or the prior C5 research stages.

## Earlier v0.1.3 milestone (historical)

Current development candidate: GUI v0.1.3 meter-raw, with explicit read-only
INA228 ID/configuration/raw-register diagnostics. It is not a calibrated meter.
The owner installed v0.1.3 and normal-booted it; five HID-only raw snapshots
succeeded. Package SHA-256:
`22cef1285ee090474931959fba659cc5304c45500f276008c9f6450fc48746db`.

The preceding GUI-only v0.1.1 button-fix was compiled for the owner's bootloader.
Owner reports the physical row Back / Left(-) / OK / Right(+), but v0.1 emitted
Left / Right / OK / Back. Fixed the C5 native mapping to PB14 Back, PB15 Left,
PA13 OK, PA14 Right. Upstream navigation/rendering and Rust flip handling are
unchanged. The owner subsequently confirmed the corrected assignments.
Current outputs: `build/gui-v0.1.3-meter-raw`. Earlier candidate outputs, captures
and v0.1.1/v0.1.2 source snapshots remain intact.
Unmodified upstream renderer/navigation; one documented pure-history const
constructor patch, pinned in `upstream-patches.json`. Upstream original commit
`a454c8e6ba5a84747ad6da2928a724e3e714945c`, original tree pinned separately.

17 pages plus settings, proportional LCD scanout, four buttons, manual flip and
brightness. Unsupported settings/query/trigger operations are blocked. C5 meter
ID and raw reads now work through the diagnostic host command; no calibrated
GUI measurement, line/ripple ADC, PD or legacy-protocol driver; no runtime flash writes.
Settings are RAM only. Every page declares the incomplete hardware status.
On 2026-11-17 the owner reported installing and normally booting this candidate.
A host-access monitor received GUI status successfully; see physical status below.

Current package evidence is in `docs/VALIDATION.md`,
`build/gui-v0.1.3-meter-raw/manifest.json` and `source-hashes.json`. Host
previews are in `build/previews`; they contain no simulated measurements.
Six Rust and eight Python tests passed for v0.1.1, including the real C GPIO
decoder across all 16 button combinations. ARM link and synthetic preservation
audit passed. Package SHA-256:
`9856b468680d3d776c262161242f1a64c0a566b693581ba64bba1d2b57fdfe11`.
ARM link and bounded synthetic installation audit passed. Startup stack copies
were eliminated with `App::init_in_place` and inline-const empty History.
Largest local static estimate 2428 bytes; init 456 bytes; guard 9472 bytes plus
reserved stack8192. These are not actual hardware stack measurements.

## Physical next step

v0.1.1: owner confirms normal startup/correct buttons; 30-second telemetry is
`build/captures/gui-20261117-103058.jsonl` (about 10 fps, LCD 37 ms, error 0,
guard 9,472 bytes, max polling gap 20 ms). Full dual readback at
`build/gui-v0.1.1/captures/dfu-20261117-103322` matches activated package and
passes all preservation checks. Complete Flash SHA-256:
`b738cc56813da2e7c3f3e91ed52078d112b72869c801e1e5df89b665774ba8c4`.

v0.1.2: real ID probe read INA228 at 7-bit `0x40`, PB8 SCL/PB9 SDA,
manufacturer `0x5449`, device `0x2281`, in 6 ms. Log:
`build/captures/meter-id-20261117-105554.json`.

v0.1.3: five raw snapshots with only side HID connected succeeded, 30 ms each.
CONFIG `0x0000`, ADC_CONFIG `0xFB68`, SHUNT_CAL `0x1000`; bus/shunt codes are
near zero. GUI stays error 0, guard 9,472 bytes; explicit raw probes increased
the maximum polling gap from 19 to 49 ms. Log:
`build/captures/meter-id-20261117-110808.json`. See `docs/METER-INVESTIGATION.md`.
The user was asked to connect only a 5 V source to the main measurement input,
without load, keeping HID connected, for the next comparison. No calibration,
reference accuracy, ADC freshness/coherency or GUI meter operation is qualified.

Next: record 5 V/no-load raw samples and reference conditions; trace stock
calibration loading; qualify fresh measurements before updating the GUI. Later
images also require their own dual DFU audit; current verify default is v0.1.3.

### Earlier v0.1 observations

Sandbox enumeration returned zero matching HID devices. Host-access enumeration
detected one qualified owner C5 after the owner's installation report. The
assistant did not flash hardware. Read-only telemetry at 09:54 JST returned GUI,
error 0, about 10 fps, LCD 37 ms, max polling gap 10 ms and intact 9,472-byte
guard. The 30 samples cover only the initial page with no buttons pressed.
Log: `build/captures/gui-20261117-095412.jsonl`.
The v0.1.1 correction and its full readback were subsequently confirmed above.
This replaces the DOOM application; accepted v7 rollback remains under
`D:/doom_on_km003c/local/c5-research/c5_stage8/build`.
After the GUI test, enter DFU and run `verify.ps1 --dfu` for dual full readback
and preservation audit. Do not call host checks a physical success.

## Follow-on work

Follow `docs/PORTING.md`: identify C5 sensing circuitry/transport/calibration,
validate fresh real measurements, connect shared totals/history/max logic,
then line/ripple ADC, passive PD receive and active operations. The KWS hardware
IC identities, pins, flash map and flasher are not C5 definitions. All original
owner stock images/backups remain only in the old C5 research folder and are
not included in source/release deliverables.

INA228 ID and its PB8/PB9 transport are now physically observed. Calibration
loading remains unresolved. Stock pointers: `0x0800C808` raw history queue,
`0x08007634` mean, `0x0801F11C` / `0x0801F1E8` current/voltage conversion,
`0x08062DA4` default endpoint selection from `0x080AE208`; correction/settings
RAM around `0x20000674` / `0x20002994`. These are static-analysis pointers, not
the owner's recovered calibration. Never assume a shunt resistance from them.

Local Rust/LLVM/cache defaults are in `tools/build.py`; builds are offline and
read-only toward USB. Root git repository was initialized for this new port;
no remote publication, GitHub comment, release or hardware programming by the
assistant occurred.

## Workspace migration

Relocation is complete. `Cargo.toml` is directly under `D:/c5_standalone_rs`.
The initial copy verified 255 files and omitted regenerable caches. At the
owner's subsequent request, all 2,942 legacy files, including Git metadata and
caches, were preserved and SHA-256 checked in
`build/migration-completion-20261117-161436/legacy-workspace/` before removing
the old subdirectory. The current v0.1.9 workspace remains authoritative.
See `docs/MIGRATION.md` and the completion directory's preservation manifest.

Use `--cargo-home D:/c5_standalone_rs/.cache/cargo` when building. A local copy
of the available dependency cache was prepared so Cargo does not write into
the KWS-X1 project. The current script defaults to the local cache. External
toolchain locations, bootloader and baseline references intentionally
remain under the protected C5 research directory.

Relocated host tests (6 Rust / 7 Python), preview equality and ARM build passed.
The local-cache ARM rebuild contains changed embedded dependency paths and has
a different digest. It is preserved separately in `build/relocated-rebuild-20261117`.
The original hash-pinned candidate and matching build evidence are restored at
their normal `build/` paths; do not conflate the two binaries.
