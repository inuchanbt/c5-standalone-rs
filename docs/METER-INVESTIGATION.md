# C5 meter identification: static evidence and diagnostic candidate

2026-11-17. GUI v0.1.1 now has owner-confirmed button mapping, healthy GUI
telemetry and a successful full dual DFU readback/preservation audit. The next
milestone is identifying the actual meter IC and its calibration path.

## Evidence from the stock image

Input: the owner's existing stock V8.5 application payload, 719,100 bytes,
SHA-256 `51d57d31a3d3b2fafbc18defcadeedf964bd418e0954543426ac6fc818e51682`.
Its external path is recorded in `research/stock_meter_evidence.py`; the image
and private device backups are not copied into source deliverables.

The following table records static observations. A later physical ID read is
recorded separately below.

| Stock address | Observation |
| --- | --- |
| `0x0800AF2C` | Software I2C byte transmitter: GPIOB mask `0x100` clocks, `0x200` carries data, including ACK sampling |
| `0x0800AE54` | Matching byte receiver and master ACK/NACK |
| `0x0800AFFC` / `0x0800B064` | START / STOP sequences on the same pins |
| `0x0800B120` / `0x0800D7C4` / `0x0800D7E8` | PB8 clock setup and PB9 input/output direction helpers |
| `0x0800B486` | Register-pointer write to address byte `0x80`, repeated START with `0x81`, two received bytes |
| `0x0800B4C4` | Same fixed address, three received bytes |
| `0x08007194` | Reads register `0xFF`, compares upper 12 bits with `0x226` |
| `0x080071F0` | Reads register `0x3F`, compares upper 12 bits with `0x228` |
| `0x0800724C` | Reads register `0x3E`, compares with `0x5449` |
| `0x08007294` | Selects different identification/init/sample function pointers; the stock image supports several paths |

The two address bytes imply a 7-bit address of `0x40`. The GPIO masks identify
PB8 as clock and PB9 as data in this stock path. The register comparisons match
TI's [INA228 data sheet](https://www.ti.com/lit/ds/symlink/ina228.pdf) and
[INA226 data sheet](https://www.ti.com/lit/ds/symlink/ina226.pdf): each defines a
manufacturer/device ID pair. This identifies supported stock-driver paths; it
does **not**, by itself, identify which IC is fitted to the owner's C5.

`research/stock_meter_evidence.py` rechecks the complete input hash, selected
entrypoint signatures and GPIO literal pools. Its report is
`build/research/stock-v85-meter-evidence.json`. The interpretations in the table
come from manual instruction/control-flow review, not from that signature check
alone. The KWS-X1 driver and its pin mapping are not the basis of this evidence.

## v0.1.2 meter-ID candidate

Package: `build/gui-v0.1.2-meter-id/C5-standalone-GUI-v0.1.2-meter-id.c4ser`.
SHA-256: `4478395d9680968b1e2683b012a43f0ac7f0522a3a9092efbcb351592ffb0729`.

This candidate retains the corrected four-button GUI. It adds one host-requested
ID probe, with no probe at startup or during ordinary GUI monitoring. Only the
fixed address `0x40` and ID registers `0x3E/0x3F` then, if necessary, `0xFE/0xFF`
are readable. It stops early for a matching INA228 pair. It labels INA226/INA228
only when both the expected manufacturer and device identity match. Other
results remain unknown.

The I2C write phases send only the address and register pointer required for
a read. No register-value write, reset, calibration/configuration update, scan,
bus-recovery clock train, PD/legacy-protocol control or Flash programming is
implemented. GPIO access changes only PB8/PB9 configuration nibbles/latches;
both lines are released as pull-up inputs for high and driven only low. The
backlight boot setup configures PB7; its timer compare write is `0x40000838`,
so these PB8/PB9 changes do not change that pin's configuration.

The probe has a 25 ms tick deadline, 5,000 pause-call ceiling and 32-pause
clock-release wait limit. It stops after NACK or timeout, records the failed
register/phase and releases both lines. Timing and pull-up suitability remain
physically unverified; no exact I2C frequency is claimed. The GUI can incur a
polling gap during this explicit one-shot probe.

The reply contains raw ID registers, validity bits, initial line levels, elapsed
time and error location. It contains no voltage/current values. Sensor raw
measurement reads, configuration, shunt resistance, calibration, freshness and
conversion are later milestones. The GUI continues to display unavailable
measurements.

## Offline checks

Fifteen Python tests passed, including execution of the real C transaction
engine against injected INA226/INA228 identities, wrong manufacturer IDs,
address/pointer/read NACKs, busy bus, stuck clock and expired deadline. Recorded
outgoing waveforms contain only address/pointer/read transactions and final-byte
NACKs; no sensor-value writes or retries. These are host-injected line samples,
not an electrical simulation or hardware proof.

ARM compilation/link, pinned upstream/build inputs, stack checks, package round
trip and synthetic installation over the physically verified v0.1.1 readback
passed. Static RAM remains 72,448 bytes and the extra guard remains 9,472 bytes.
The raw image is 88,150 bytes. New-image boot and actual I2C behavior are pending.
The physically verified v0.1.1 package, source snapshot and readbacks remain
under `build/gui-v0.1.1`.

## Physical next step

1. From DFU, install the v0.1.2 meter-ID package using the official WITRN updater.
2. Close the updater and reconnect normally. Check the corrected GUI still works.
3. From `D:/c5_standalone_rs`, run `probe-meter.ps1` with host HID access.
   It checks healthy GUI status, sends one probe, records the reply and checks
   GUI status again. Existing output evidence is never replaced. Stop other
   C5 HID clients before running it.
4. On NACK/busy/timeout/unknown ID, retain the record and investigate that stage;
   do not interpret it as absence of all sensors. No automatic retry is made.
5. After identifying the device, compare the matching stock sample/configuration
   path and qualify read-only raw samples. Only then design configuration and
   calibrated measurements. Repeat dual DFU readback after the new image trial.

## Physical ID result: v0.1.2

The owner installed the candidate and booted normally. The explicit ID request
in `build/captures/meter-id-20261117-105554.json` returned manufacturer `0x5449`
and device `0x2281` at registers `0x3E/0x3F`, identifying INA228 on this C5 at
`0x40`. The two reads took 6 ms. GUI state/error stayed GUI/0 and the extra guard
remained 9,472 bytes; max polling gap changed from 10 to 11 ms. This qualifies
that ID transaction, not calibration or all operating conditions.

## Raw diagnostic: v0.1.3

Package: `build/gui-v0.1.3-meter-raw/C5-standalone-GUI-v0.1.3-meter-raw.c4ser`.
SHA-256: `22cef1285ee090474931959fba659cc5304c45500f276008c9f6450fc48746db`.

This extension repeats the ID check before every snapshot and then reads only
registers `0x00..0x06`: CONFIG, ADC_CONFIG, SHUNT_CAL, SHUNT_TEMPCO, VSHUNT,
VBUS and DIETEMP. VSHUNT/VBUS are received as three bytes; the others use two.
No configuration/calibration value is written. DIAG_ALRT is deliberately not
read, avoiding read-to-clear flags. Arbitrary register/device access is not
exposed over USB. The full snapshot has a 50 ms deadline and 10,000 pause-call
ceiling. The ID-only request retains its 25 ms limit.

Run `probe-meter.ps1 --raw --samples 5` with other HID clients closed. It makes
five snapshots 0.5 s apart and checks GUI status before and after. Raw fields
have explicit validity bits; partial reads retain the exact error stage. These
sequential register reads are not an atomic/coherent ADC frame, and freshness
has not been qualified. No raw sample reaches the GUI history, maxima or totals.

Eighteen Python tests, ARM compilation/link, stack/input checks, package round
trip and synthetic preservation audit passed. The six Rust GUI tests passed
with unchanged Rust inputs. Static RAM is still 72,448 bytes, extra guard 9,472
bytes, raw image 88,558 bytes. Previous candidates and pinned source snapshots
are preserved separately.

### HID-only physical result

The owner reports only the side HID connection, with no main input or load.
All five snapshots in `build/captures/meter-id-20261117-110808.json` succeeded:

| Register / observation | Result |
| --- | --- |
| CONFIG / ADC_CONFIG | `0x0000` / `0xFB68` in all samples |
| SHUNT_CAL / SHUNT_TEMPCO | `0x1000` / `0x0000` in all samples |
| VBUS 20-bit code | 0 or 1 |
| Signed VSHUNT 20-bit code | -1 to 8 |
| DIETEMP raw | `0x0EAE` or `0x0EAF` |
| Full snapshot time | 30 ms each |
| GUI state / error / guard | GUI / 0 / 9,472 bytes before and after |
| Maximum polling gap | 19 ms before, 49 ms after the diagnostic burst |

TI's nominal chip scaling gives 0..195.3125 µV bus voltage and -0.3125..2.5 µV
shunt voltage for these codes and the observed ADC range. Those are uncalibrated
diagnostic conversions, not reference-meter comparisons or calibrated C5 values.
Current cannot be inferred without qualified shunt/calibration information.
The parser checks were independently replayed on all saved wire frames; the
analysis is `build/gui-v0.1.3-meter-raw/hardware-validation-hid-only-20261117.json`.

The one-shot snapshot blocks foreground button polling for part of its roughly
30 ms duration. A production measurement scheduler should avoid reading identity
and all configuration registers on every sample, and qualify actual polling gaps
before connecting the driver to the GUI.

### Calibration investigation pointers

Stock function `0x0800C808` queues raw history and `0x08007634` averages it;
neither is itself a physical-unit conversion. Stock callers use `0x0801F11C`
and `0x0801F1E8` for current/voltage conversion, with endpoint/offset data in RAM
around `0x20000674` and the settings structure at `0x20002994`.
`0x08062DA4` selects default endpoint data from stock constant table
`0x080AE208` according to the detected sensor kind. These are static analysis
pointers only. Persistence loading and the owner's actual correction values
are not yet traced; do not treat those default table entries or SHUNT_CAL's
observed value as the complete factory calibration or a proven shunt resistance.

### Phihong 5 V / unloaded physical result

The owner connected Phihong AA240U-59FKEA-R to the main input while retaining
HID, with the output unloaded. Five more snapshots in
`build/captures/meter-id-20261117-112650.json` succeeded. Nominal chip-scaled bus
voltage was 5.15859375..5.162890625 V; shunt voltage was -3.75..0.3125 µV.
CONFIG/ADC_CONFIG remained `0000/FB68`. GUI/error remained GUI/0 and guard
9,472 bytes; maximum polling gap remained 49 ms. The source's 5 V capability is
listed in [Phihong's specification](https://www.phihong.com/products/aa240u-59fkea-r-2/).
Its actual output was not yet independently measured during this capture.
These data demonstrate response to the connected input, not calibrated accuracy.
The separate diagnostic analysis is
`build/gui-v0.1.3-meter-raw/hardware-validation-phihong-no-load-20261117.json`.

## External settings/calibration read path and v0.1.4 candidate

Further stock review located the persistent-load path:

- `0x0800787C` reads `0xEA` bytes from logical external address zero through
  `0x0800A364`; startup passes the settings structure at `0x20002994`.
- `0x0800A364` generates write/read address bytes from `0xA0/0xA1` plus the
  high address bits, then an 8-bit pointer. This addresses the stock logical
  `0x000..0x7FF` region through 7-bit addresses `0x50..0x57` on PB8/PB9.
- Stock integrity checks `0x0800B54C`, `0x0800B5A0`, `0x0800B584` and
  `0x0800B564` check blocks ending at offsets `0x1B`, `0x6F`, `0x9F`, `0xE9`.
  Routine `0x0800AAE0` computes XOR of each block's data bytes, then XOR `0xA5`.
- The loaded structure is consumed by the current/voltage conversion routines
  above. Actual captured values and their interpretation remain to be verified.
- **Do not call stock storage initialization**: `0x0800A3E2` performs a
  write/read marker test at logical `0x7FF`; invalid settings can invoke default
  replacement paths. Those write-side routines are not included in this port.

v0.1.4 adds a fixed read-only external-storage interface and the collector
`backup-storage.ps1`. It reads 128 aligned 16-byte blocks, then reads all blocks
again in descending order with a different nonce. It requires exact equality of
both 2 KiB files, independently reopens/hashes them, reports the four stock
checksum results, and checks GUI status before/after. It neither repairs invalid
checksums nor loads default settings. It exposes no storage write operation,
arbitrary I2C address or arbitrary pointer/length request.

The external data are private device data and are saved only under ignored
`build/private-storage/`; never include these files or packet traces in a public
release. Source snapshots explicitly exclude all build/capture data. A complete
read is not yet a qualification of factory calibration or external IC type.

Package: `build/gui-v0.1.4-cal-read/C5-standalone-GUI-v0.1.4-cal-read.c4ser`.
SHA-256: `0415afb834cf3f431e825dbc2899299de676d9bb2bce7997b801d8b851967355`.
The raw/ID diagnostics remain available; no diagnostic runs at startup.
Twenty-five Python tests passed, including all 128 read-block address/pointer
waveforms, range rejection without GPIO activity, NACK cleanup, cross-pass nonce
rejection and checksum corruption rejection. ARM link, source/stack checks,
package round trip and synthetic preservation audit passed. Raw image 89,238
bytes, static RAM 72,448 bytes, extra guard 9,472 bytes. The owner booted this candidate, but its continuous read failed after 24
blocks with an LCD timeout. See the failure and repair record below.

The Python collector was exercised with an injected HID device: both pass
orderings and distinct nonces, retaining mismatched copies without claiming
completion, stopping after one NACK without retry, and refusing to overwrite
an existing output directory. These are host checks, separate from hardware.

### KM003C comparison at the same nominal 5 V condition

The owner inserted a POWER-Z KM003C between Phihong and C5 and supplied a photo.
Its display reads 5.154168 V, 0.000946 A and 0.004875 W. The C5 output remained
unloaded and side HID connected. The photo also shows the GUI's unavailable
measurement fields and incomplete-driver footer, as expected for this stage.

A fresh five-sample capture, `build/captures/km003c-comparison-20261117.json`,
gave nominal INA228-scaled bus voltage 5.15234375..5.1556640625 V, mean
5.154296875 V. Per-sample differences from the photo are approximately
-1.824..+1.496 mV. The photo and raw reads are not exactly synchronous, the
comparison instrument's traceable calibration is unknown, and this is one
voltage/no-load condition. It supports functional agreement near 5 V, not
general accuracy or invented calibration coefficients. The local analysis is
`build/gui-v0.1.3-meter-raw/hardware-validation-km003c-comparison-20261117.json`.
GUI error remained 0, guard 9,472 bytes; flipped orientation was observed.

The subsequent v0.1.3 full dual DFU readback at
`build/gui-v0.1.3-meter-raw/captures/dfu-20261117-115056` passed application and
all preservation checks. Full Flash SHA-256:
`aa9045860860a4e7ce6d5dc1b312e092ddf45b19b21093417f72ecc97aef1faf`.

## v0.1.4 scheduling defect and v0.1.5 repair

Actual HID-only read: `build/private-storage/read-20261117-115704`. First 24
blocks succeeded (384 bytes), then GUI_NOT_READY; follow-up GUI log
`build/captures/gui-20261117-115823.jsonl` shows LCD timeout/error 1, guard
9,472 bytes. Each successful storage job took approximately 12 ms. Servicing
successive requests inside LCD row scanout stretched one frame past its 250 ms
wall-time deadline. The private recovered prefix and wire evidence remain
incomplete; matching checksums for the first 234 bytes do not establish a full
backup. No storage writes occurred through this interface.

v0.1.5 queues ID/raw/storage requests received during scanout and executes them
only outside it, retaining the original request prefix/nonce. It retains the
250 ms LCD timeout and fixed read-only ranges. GUI_NOT_READY is now reported
clearly even when an older firmware reply lacks a valid storage offset.
Twenty-eight Python and six Rust tests passed; actual queue code, old-timeout
clock model, ARM link and package/preservation checks passed. These are host
checks; physical validation of the fix remains pending. Package SHA-256:
`fec596fdcd07473f93793334c2888e6fafa0597a6a631e2ef77a7aa50dfaa6f5`.
Next: full internal audit of installed v0.1.4, owner installation of v0.1.5,
then independent ascending/descending reads of the private external 2 KiB.

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

## Stock conversion reconstruction after the private backup

Further instruction review ties INA228 to stock sensor kind 0 (`0x08007294`),
which selects `[0, 204800, 0, 409600]` from `0x080AE208` for the voltage and
current endpoints at RAM `0x20000674`. Literal doubles at `0x0801F280` and
`0x0801F1E0` are **10.0** and **2.0**, respectively; they are different scales.
Stock bus acquisition at `0x080071C8` uses `(VBUS24 >> 2) & 0x003FFFFC`.
Stock shunt acquisition at `0x08007560` sign-extends the packed 24-bit reading
(with low four bits cleared), then arithmetic-shifts by two in the narrow range.
This yields one canonical stock input scale across the two shunt ranges. The
stock code can also change ADC range; those configuration writes remain absent
from this port. The offline model uses each captured CONFIG bit 4 explicitly.

Let `Sxx` denote a signed little-endian 32-bit field at external/settings offset
`0xxx`, and `Fxx` a little-endian float32 field. For kind 0, the reviewed
conversion functions reconstruct approximately as:

- Voltage: `qV * (10 + F10) / (204800 + S04 + S4F)`.
- Current before deadband: `(qI - S08) * (2 + F14) / (409600 + S0C + S53 - S08)`.
- Stock kind-0 current deadband: values from about -0.002 through +0.001 become zero.

These are stock-code research formulas, not a newly measured calibration.
The real implementation converts filtered inputs/intermediate values through
float32 and double operations; the preceding moving-average pipeline is not
reproduced by a single raw snapshot. The provenance and UI meaning of each
correction field remain unqualified; neutral offset names deliberately avoid
calling every field a factory coefficient. A physical shunt resistance must
not be declared from this table or SHUNT_CAL alone.

`research/calibration_decode.py` verifies the pinned stock hash/constants,
reopens both matching private copies, verifies their hashes/four checksums and
writes decoded fields/model samples only into the same ignored private capture
directory, refusing existing outputs. It never opens USB. Offline consistency
checks covered the default 10 V endpoint, equivalent wide/narrow 2 A inputs,
negative-current sign and corrupt-settings rejection. Those are model checks,
not physical measurements. Applied to the earlier KM003C comparison capture,
the private model produced approximately 5.15144..5.15476 V; this remains a
non-synchronous no-load comparison at one voltage, not an accuracy qualification.

The firmware and its frozen source snapshot remain unchanged by this later
research script. Next physical work requires a known 5 V load/current comparison,
then a bounded sampling scheduler with verified freshness before any readings
enter GUI/MAX/history/energy. The owner has been asked what load is available;
leave the device in DFU until the next physical setup is agreed.
