# v0.1.7 INA228 conversion-ready experiment

The v0.1.6 shadow sampler now has physical timing/load-response and full Flash
preservation evidence. Cache sequence/timestamp changes establish new register
acquisition; they do not independently establish a new ADC conversion. This
experiment investigates that remaining distinction before GUI measurement use.

The [TI INA228 data sheet](https://www.ti.com/lit/ds/symlink/ina228.pdf), sections
7.3 and 7.6.1.12, defines DIAG_ALRT register `0x0B`, CNVRF bit 1 and MEMSTAT bit 0.
Reading this register can clear latched status. Observed flag patterns must be
recorded rather than assuming an acquisition counter proves ADC freshness.

The new **explicit host-only** `C5F1`, command `9E`/reply `9F`, performs:

1. Existing fixed INA228 identification at address `0x40`, PB8/PB9.
2. CONFIG/ADC_CONFIG reads. Only the observed `0000/FB68` pair is accepted.
3. Eight consecutive 16-bit DIAG_ALRT reads, preserving every raw word.

It refuses the experiment while the shadow sampler is active. It is never run
at boot, ordinary raw reads or GUI monitoring. GPIO/I2C work is deferred until
outside LCD scanout, with a 60 ms deadline and bounded pause count. NACK/timeout
stops without retry, preserving completed words and failed register/phase.
Both bus lines are released after failure. There are no sensor configuration,
calibration, storage-value or Flash writes. **Read-to-clear flag side effects
are intentional and remain distinct from those absent value writes.**

`probe-fresh.ps1 --samples 5` records five independent experiments, raw HID
packets, ready/memory/latch bits, elapsed times and GUI status. No observation
is automatically marked as qualified ADC freshness, and no reading enters the
GUI/MAX/history/energy. A constant flag, error or unsupported configuration
must be investigated; it is not interpreted as sensor absence.

The package is under `build/gui-v0.1.7-ready-flag`; earlier packages and frozen
sources remain intact. Initial physical test uses side HID only, main path
disconnected and ASD LOAD OFF. This candidate has passed host checks but has
not yet been installed or physically tested. Source/provenance/package checks
and an independent later full dual DFU audit remain separate evidence stages.

Host tests execute the actual native read engine, verify its exact read-only
address/register waveform, all eight preserved words, identity/config gating,
partial NACK/timeout cleanup and stale/corrupt/false-success wire rejection.
These checks do not model the analog sensor or the real read-to-clear timing.

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
