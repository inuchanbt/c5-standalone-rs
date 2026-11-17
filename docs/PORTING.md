# C5 port: hardware evidence and next milestones

Current outcome: **v0.1.9 experimental Overview is confirmed on the owner's
unit**, including loaded V/I/power/MAX, missing main values after STOP, retained
MAX and full dual-Flash preservation audit. See [STATUS.md](STATUS.md) for the
public summary and [CHANGELOG.md](CHANGELOG.md) for the candidate sequence.

## Reused and qualified elsewhere

The existing C5 DOOM project physically established the LCD, four key inputs,
normal application boot and bootloader USB transport on the owner's unit.
On 2026-11-17 the owner reported installing and normally booting the Rust GUI
candidate. Its GUI USB status and initial-page timing/guard were then observed
on that unit. Visual/control observations and full readback are tracked
separately in [HARDWARE-VALIDATION.md](HARDWARE-VALIDATION.md).

| Interface | Evidence / implementation | Current C5 GUI status |
| --- | --- | --- |
| App boot | Vectors at `0x08004000`, `C400` tag at `+0x810`, activation at `+0xC00` | v0.1.9 normal operation and full dual installation readback passed |
| LCD | Boot-established SPI3, PB4 D/C, PA15 CS, MADCTL `0x60`, row offset 34 | GUI counters/timing and v0.1.9 owner panel photographs confirmed |
| Buttons | Physical Back/Left/OK/Right = active-low PB14/PB15/PA13/PA14 | Owner confirms corrected v0.1.1 mapping |
| Backlight | Boot entry `0x08001E35`, PB7, compare register `0x40000838`, original ARR 99 | RAM-only brightness control implemented; 95% observed in v0.1.1 telemetry |
| USB | Existing boot ISR at `0x080029ED`; foreground validation and response | Read-only GUI status observed on one C5 |
| Measurement | INA228 at `0x40` via PB8/PB9; checked runtime settings and gated conversion | v0.1.9 experimental Overview/MAX confirmed at fixed 5 V; wider range, accuracy and calibration provenance remain unqualified |
| D+/D-/CC ADC | Divider ratios, ADC channels and valid range not established | No driver; unavailable readings |
| PD PHY | Controller identity and C5 routing not established | No driver or requests |
| Legacy protocols | C5 drive circuitry not established | No output driver |
| Storage | Stock-addressed 2 KiB read path identified; v0.1.4 partial capture retained | v0.1.5 external dual read/checksums and internal Flash preservation audit passed; runtime writes absent |

The upstream firmware targets HC32F460 and uses a FUSB302 controller and INA226
meter adapter. Those are facts about KWS-X1; they are **not C5 component IDs**.
The shared protocol crates remain available as pure logic, but no HC32 register,
GPIO, timer, ADC, I2C, DMA or flash setup is executed on C5.

The INA228 identification above comes from C5 stock-code analysis and the C5's
actual ID response, independently of the KWS-X1 sensor. See
[METER-INVESTIGATION.md](METER-INVESTIGATION.md). The previous backlight label
"CCR3" was imprecise; exact boot instruction review shows offset `+0x38` and
PB7 setup. PB8/PB9 probing preserves that PB7 configuration.

The v0.1.5/0.1.6 load comparisons, v0.1.7 clear/set observation, v0.1.8 per-cache
gate and v0.1.9 experimental GUI integration are recorded. Next, qualify sample
timing before connecting history/energy. Analog accuracy, same-cycle atomicity,
wider ranges, line/ripple ADC and PD drivers remain unqualified.

## Completion sequence

The owner's v0.1 trial identified that the physical row is Back / Left(-) / OK /
Right(+), while the old adapter emitted Left / Right / OK / Back. The v0.1.1
native decoder now follows the physical labels. This pin-to-label association
comes from the owner's observed behavior plus the previous GPIO decoder; it is
not a new electrical probe. Only logical Left and Right are exchanged by the
existing Rust rotation handling; Back and OK retain their functions.

1. **GUI physical check (initial milestone completed):** official update, cold boot, every page, all keys,
   180° rotation, brightness, telemetry and full dual readback. Inspect real
   button polling gaps and stack guard before adding peripherals.
2. **C5 meter driver (Overview/MAX milestone completed; continue qualification):** identify the sensing IC and transport from the owner's
   stock image/board evidence; establish raw reads and calibration provenance.
   Compare zero-current and known-voltage/current points with a reference meter.
   Only validated fresh samples may update overview, maxima, history and totals.
3. **Lines and ripple:** qualify ADC channel mapping, divider/reference scaling,
   bandwidth and timing. Do not report ripple from a slow DC-only meter channel.
4. **PD receive:** identify the PHY/routing and implement a passive receive path
   with captured frames compared with CY4500-EPR. Reuse parsing and UI logic.
5. **Active PD/cable/charger operations:** validate CC orientation, GoodCRC,
   roles, message IDs, negotiated limits and recovery before enabling requests.
   Qualify SPR first, then EPR reception/queries and supported triggers.
6. **Legacy protocols, persistence and export:** map the actual output circuits;
   qualify each protocol, then define C5-specific settings/logger/capture regions.
   KWS-X1 addresses and erase geometry are not portable storage definitions.

## Verification limits

Host tests exercise the real Rust renderer/navigation and the new display map,
blocked actions and settings. Package tests exercise encoding, corruption
rejection and preservation checks. A successful ARM link proves image layout
and symbol resolution; it does not prove peripheral correctness, stack peak,
button responsiveness or a successful update. Host previews contain no simulated
measurements and are not evidence that the C5 sensing hardware works.

## Experimental Overview candidate

v0.1.9 connects checked runtime conversion and the gated cache to Overview/MAX.
Host, HID, loaded conversion, owner panel and dual-Flash audit checks passed.
See [METER-DISPLAY.md](METER-DISPLAY.md). History,
energy, line/ripple ADC and PD remain later milestones.
