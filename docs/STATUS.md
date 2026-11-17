# Current milestone and public validation summary

English is authoritative. Status as of **2026-11-17**: **v0.1.9 experimental live
Overview is confirmed on the owner's C5**. The project ports the KWS-X1 Rust GUI
and will continue toward C5 measurement and protocol support.

## Implemented scope

The upstream renderer/navigation is pinned to
`a454c8e6ba5a84747ad6da2928a724e3e714945c`. All 17 pages and settings are available;
unsupported actions stay blocked. The original 240 × 135 GUI is scaled to
306 × 172 and centered on the 320 × 172 panel. Physical keys are Back / Left /
OK / Right on PB14 / PB15 / PA13 / PA14. Rotation, arrow swapping and brightness
are RAM-only.

C5 INA228 identity was observed at `0x40` over PB8/PB9. Runtime reads the first
240 external-settings bytes twice outside LCD scanout, requires equality, four
stock checksums and bounded fields, then starts acquisition. Each published
sample requires an observed conversion-ready clear-to-set transition and
complete bounded reads with unchanged `0000/FB68` configuration.

Converted millivolts/signed milliamps feed Overview power and RAM-only MAX.
Accepted display envelope: **0..5.5 V and |I| <=1.1 A**. Cache expiry is 500 ms;
STOP/fault/expiry removes main readings while retaining MAX. STOP disables
autonomous renewal until reboot. Display limits do not control or disconnect
the power path. Sensor register values, external stored values and runtime
Flash are not programmed; diagnostic status reads can clear flags.

## Evidence and its limits

| Evidence class | Observed result |
| --- | --- |
| Host, at v0.1.9 packaging | 11 Rust integration tests and 85 Python/native tests passed; 38 private captured vectors matched the offline conversion model after mV/mA rounding |
| Static/link/package | ARM link, upstream/source pins, package round trip and synthetic preservation audit passed |
| HID-only hardware | 20 s, 191 telemetry rows, all 75 consecutive display sequences observed, settings READY, GUI error 0, sentinel guard 8,928 bytes |
| Earlier raw bench | v0.1.8 fixed-5 V comparisons at energized 0, 0.1, 0.5 and 1 A completed; no broad accuracy claim |
| v0.1.9 loaded telemetry | 10 paired raw/gate/display sequences matched; 5.071..5.081 V and signed -101..-103 mA |
| Observed 20 s trial | 20 paired sequences matched; 5.071..5.076 V and -101..-102 mA, GUI error 0 and guard 8,928 bytes; ASD LOAD OFF and sampler STOP confirmed at end |
| Owner/panel | Owner confirmed values and MAX, dashes after STOP, retained MAX; photographs show 5.07 V / 0.10 A / 0.51 W and MAX 5.10 V / 0.10 A / 0.52 W |
| Installed image/storage | Two full 1 MiB internal-Flash reads matched; activated package, boot/factory header, erase tail and bytes beyond the application erase range passed |

The observed trial used Framework -> Sumitomo 1.0 m -> CY4500-EPR -> C5 ->
ASD-PD31, C5 PD OFF, fixed 5 V / 0.1 A. Current magnitude from the offline
conversion averaged 1.588272 mA above ASD's reading in this trial. No fitted
correction was applied; devices at different path positions and bracketed read
times do not establish simultaneous, traceable calibration. Signed telemetry
is preserved; the upstream panel shows magnitude and direction.

The raw image is 98,150 bytes; static RAM 72,992 bytes; reserved stack 8,192
bytes; additional sentinel guard 8,928 bytes. Largest syntactic local-frame
estimate: 904 bytes. Static estimates and an intact observed guard do not
establish the complete call-tree/interrupt peak stack requirement.

After later host-only bench checks were added, publication checks reran the
current host suites: **11 Rust integration tests and 89 Python/native tests
passed**, and all 17 page previews plus settings were regenerated with the real
Rust renderer. Upstream source pins were checked by the host build. The tested
firmware and its frozen build source snapshot were not regenerated for publication.

## Package and local evidence

Tested package: `C5-standalone-GUI-v0.1.9-meter-display.c4ser`.

SHA-256: `f05abfd3bfa141f498099c2d27dd9349c0ba49a61d34560581d0f0abcc9f830d`.

Owner-local evidence is preserved under ignored `build/`:

- `gui-v0.1.9-meter-display/overview-milestone-20261117.json`: final aggregate;
  supersedes pending fields in earlier stage reports.
- `captures/display-20261117-154353-282929`: first HID-only display test.
- `captures/bench-20261117-155448-243078`: first loaded display comparison.
- `captures/bench-20261117-160326-749737`: observed 20-second trial.
- `gui-v0.1.9-meter-display/captures/dfu-20261117-155903`: full dual-Flash audit.
- `gui-v0.1.9-meter-display/owner-visual-20261117`: original four photographs
  and their hash manifest. Two selected photographs are published in `images/`.

Raw Flash, external settings, decoded owner coefficients, raw measurement logs,
tool caches and the migrated legacy workspace remain local. The source
publication includes this summary and selected panel photos, not those inputs
or a firmware release. Build-time `hardware_tested=false` fields are historical
build statements, not the final milestone outcome.

## Remaining work

1. Qualify sample timing and connect validated samples to history/graphs and
   energy totals, including invalid/stale intervals and resets.
2. Extend voltage/current range and calibration/reference comparisons.
3. Establish actual C5 line/ripple ADC mapping, scaling and bandwidth.
4. Identify C5 PD hardware/routing and verify passive receive against captures.
5. Qualify active cable/charger requests and supported legacy protocols, then
   C5-specific persistence/export.

KWS-X1 ICs, pins and Flash layout are not C5 specifications. Other C5 hardware
or bootloader revisions remain unqualified. Details: [PORTING.md](PORTING.md),
[METER-DISPLAY.md](METER-DISPLAY.md), [CHANGELOG.md](CHANGELOG.md).

Relocation to `D:/c5_standalone_rs` is complete; see [MIGRATION.md](MIGRATION.md).
Last observed hardware state: normal C5 boot, PD OFF, ASD LOAD OFF, C5 sampler
OFF, CY stopped and host clients closed. Publication performed no device I/O.
