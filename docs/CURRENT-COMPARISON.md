# C5 current comparison with the owner's ASD-PD31

Prepared 2026-11-17. This is a procedure, not a completed measurement record.
The owner identified the available electronic load as Asundar ASD-PD31.
Use the existing controller under `D:/ASD-PD31` read-only as a software source;
keep all new C5 data under `D:/c5_standalone_rs/build/`. Do not modify prior
ASD measurements, scripts or configuration files.

## Initial setup

- C5 firmware: physically checked v0.1.5 cal-read; no new firmware is required.
- Main path: Phihong AA240U-59FKEA-R -> KM003C -> C5 -> ASD-PD31 load input.
- C5 side HID and ASD PC-control USB remain connected to the host.
- C5 physical three-position switch: **PD OFF (physical pass-through)**.
  The manufacturer defines OFF as disconnecting the meter's internal PD circuit
  from both CC lines while preserving the through connection. ON connects one
  CC line to that circuit; E-Mark connects both for cable inspection.
  Source: [WITRN C4/C4L/C5 official manual](https://www.witrn.com/?p=1315),
  section on the three-position physical PD switch, checked 2026-11-17.
  This is manufacturer routing documentation, not a new continuity measurement
  or proof that the custom firmware implements PD.
- ASD requests **Fixed 5 V**, initially **LOAD OFF**. LOAD OFF alone does not
  establish the requested PD voltage. Confirm the KM003C voltage near 5 V.
- No voltage sweep, PPS/AVS/EPR transition, cable scan or high-voltage request.
  C5 firmware itself has no active PD control.

## Measurement sequence

1. With the user's setup confirmation, collect five read-only C5 raw snapshots
   at LOAD OFF. Record KM003C voltage/current and actual ASD state.
2. Establish 5 V / 0.1 A constant-current load, with bounded duration and LOAD
   OFF at completion. Collect five C5 raw snapshots while the condition is
   stable; record ASD measured voltage/current and KM003C voltage/current.
   A load setpoint is not an independently measured reference current.
3. Return to LOAD OFF and repeat the baseline. Inspect sign, return to zero,
   sensor range/configuration, GUI errors, LCD progress and guard.
4. Proceed to another modest current point only after the first comparison is
   consistent. Do not extrapolate a one-point result into full-range accuracy.

KM003C is upstream of C5 and can include C5 supply consumption that does not
cross the same sensing path. Preserve the unloaded baselines and both absolute
and delta-current comparisons; do not silently subtract an invented correction.
Photo/manual readings are not exactly synchronous. Host timestamps alone do not
establish ADC conversion freshness or coherent voltage/current frames.

## Existing diagnostics and offline interpretation

`probe-meter.ps1 --raw --samples 5` only reads the already qualified fixed
register set; it does not configure the sensor or change the source voltage.
Use unique output filenames for each condition and keep metadata identifying
connection order, requested current, measured current and reading times.

The stock conversion reconstruction in `research/calibration_decode.py` can
use the verified private settings backup under
`build/private-storage/read-20261117-122246`. Store decoded settings and derived
model values privately. Do not edit calibration bytes or feed these research
values into GUI/MAX/history/energy until conversion, sample freshness and
bounded production scheduling are qualified.

The existing ASD controller documents 5 V fixed timed holds and guaranteed
LOAD_OFF cleanup in `D:/ASD-PD31/docs/asd_pd31_control_manual.md`. Inspect the
actual current code and device/COM identity before issuing a load command;
never assume a historical COM number identifies the present connection.

## First attempted baseline: condition unresolved

The owner reported PD OFF / ASD 5 V / LOAD OFF and KM003C near 5 V. Five C5
raw snapshots were captured at `build/captures/current-no-load-before-20261117-124137.json`.
The owner then corrected that ASD was not LOAD OFF. Actual load state/current
and simultaneous reference values are therefore unconfirmed. The filename is
retained for evidence integrity; its `.condition.json` explicitly rejects it
as a qualified no-load baseline.

INA228 nominal bus voltage fell approximately 0.173 -> 0.063 V across the five
reads. GUI error stayed 0 and guard 9,448 bytes. This is not a stable 5 V point;
do not diagnose a wiring/sensor/source fault or current gain from this alone.
The user has been asked for actual KM003C/ASD voltage/current, ASD set current
and LOAD ON/OFF. No ASD serial port has been opened or load command sent.
Host enumeration found FTDI COM3 and CH340 COM4, but neither descriptor alone
establishes the ASD identity. Confirm it before remote load control.

### Source-off zero observation

The owner clarified that ASD LOAD OFF displays 0.000 V and KM003C approximately
0.005 V. A fresh five-sample capture is
`build/captures/current-source-off-zero-20261117-124433.json`, with a condition
sidecar. C5 nominal bus values are near zero, consistent with the reference
voltage state. This is accepted as a source-off zero observation, **not a stable
5 V / zero-load point**. Do not assume LOAD OFF maintains the source's 5 V
contract. The exact CC/attach mechanism behind supply removal is not established.
No ASD command has been sent. The owner has been asked to set Fixed 5 V / 0.100 A
and LOAD ON, then report both instruments' actual voltage/current for the first
loaded comparison. No sensor/storage configuration changes are required.

### First 0.100 A load-setting capture — reference readings pending

The owner set Fixed 5 V / 0.100 A and LOAD ON. All five raw snapshots in
`build/captures/current-load-0100A-20261117-124553.json` succeeded. GUI stayed
error 0, guard 9,448 bytes, LCD 37 ms. No ASD command or sensor configuration
write was sent. Nominal INA228 bus voltage was 5.07246..5.07578 V and shunt
voltage -308.438..-302.5 microvolts. The private stock-code conversion model
produced about 5.07157..5.07489 V and -0.102171..-0.100208 A. Keep the negative
sign: current-direction semantics remain unqualified and must not be silently
converted to absolute current in the firmware.

The owner reply contains the load setpoint confirmation but no measured KM003C
or ASD numeric readings. Those were requested separately; keep this point
pending and do not call agreement with a setpoint an accuracy qualification.
The raw `.condition.json` and private analysis record missing references as null.
Keep the 0.1 A condition until its displayed values are recorded, then perform
the return-to-LOAD-OFF observation. Further current points follow only after
this reference comparison is assessed.

### 0.100 A references and return-to-zero result

Owner-transcribed measured displays: KM003C **5.078 V / 0.1018 A**;
ASD-PD31 **5.070 V / 0.100 A**. C5 offline stock-model five-sample mean:
**5.073836 V / -0.101159 A**, current magnitude range 0.100208..0.102171 A.
Magnitude-mean difference is -0.641 mA from KM003C, +1.159 mA from ASD.
C5 voltage lies between the upstream/downstream display readings. These are
later-transcribed display comparisons at different sense locations, not exactly
synchronous accuracy measurements; no coefficients were fitted or bytes changed.
Supplemental reference report preserves the original null-reference capture:
`build/private-storage/read-20261117-122246/current-load-0100A-reference-comparison.json`.

The owner returned ASD to LOAD OFF. Five reads in
`build/captures/current-source-off-return-20261117-124911.json` succeeded;
GUI error stayed 0, guard 9,448 bytes and LCD 37 ms. Its condition sidecar
records the before/after zero observations. The shunt returns near zero with
an overlapping pre-load range; no loaded-sized residual persists. Both OFF
points have nearly zero main voltage, not an energized 5 V zero-current state.
Next proposed point: Fixed 5 V / 0.500 A with reference displays, followed by
LOAD OFF. Current sign, full-range accuracy and freshness remain unqualified.

### 0.500 A references and source-off recovery

Owner displays: KM003C **5.029 V / 0.5015 A**, ASD-PD31 **5.002 V / 0.500 A**.
Five C5 stock-model samples average **5.016268 V / -0.500606 A**; current
magnitude range 0.499696..0.501556 A. Magnitude-mean difference from KM003C is
-0.894 mA, from ASD +0.606 mA. Between the 0.1/0.5 A points, C5 magnitude rises
0.399447 A versus KM003C's displayed 0.399700 A, a -0.253 mA difference in the
increase. This is an indicative two-point functional comparison, not an accuracy
specification or a fitted calibration. Private report:
`build/private-storage/read-20261117-122246/current-load-0500A-reference-comparison.json`.
GUI error stays 0, guard 9,448 bytes, LCD 37 ms, maximum poll gap 50 ms.

The owner returned ASD to LOAD OFF; five reads in
`build/captures/current-source-off-after0500A-20261117-125335.json` succeeded,
showing near-zero main voltage/shunt and healthy GUI. Exact source-off ranges
are in its condition sidecar. Aggregate two-point evidence:
`build/gui-v0.1.5-cal-read/current-two-point-validation-20261117.json`.
Next proposed bounded comparison is Fixed 5 V / 1.000 A, followed by LOAD OFF.
