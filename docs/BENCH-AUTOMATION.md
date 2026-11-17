# ASD/CY4500/C5 automated comparison

2026-11-17. Owner-requested setup, in source-to-load order:
**Framework -> Sumitomo 1.0 m -> CY4500-EPR -> C5 -> ASD-PD31**.
Framework is the owner's source label; its exact model and mains conditions
are not established. This is separate from the Phihong/KM003C manual trials.
C5 runs v0.1.5 with physical PD OFF and side HID. ASD and CY use PC USB.

`tools/bench_compare.py` imports the existing ASD control CLI v5.8.20 and CY CLI
without editing their files. It calls ASD's `main()` for a bounded Fixed 5 V
hold and uses its existing owner-verified protocol/cleanup implementation.
CY's native capture runs concurrently, preserving EP81 PD records and EP83
scope telemetry plus raw transfers. The wrapper verifies ASD identity against
private, previously qualified evidence; no unique ASD ID is embedded in source.

Each ASD acquisition is extended into **ASD read -> C5 raw/GUI read -> ASD read**.
UTC and monotonic timestamps bound each transaction. Acquisition brackets are
about 0.52 s, not simultaneous ADC frames. CY's device clock is not declared
synchronized with C5 or host time. USB capture health, C5 faults and bounded
reference readings are checked; a failure stops load. Normal exit sends LOAD
OFF and verifies the decoded output state. The sampler is not a firmware GUI
measurement driver and does not configure the C5 sensor or storage.

## Completed Framework runs

All rows below are the CLI's steady `hold-fixed` phase. The 0.2 A prechecks in
the 0.5/1 A runs are retained separately, using actual CLI row mode/raw response
matching, not value-based rejection. C5 values are the offline stock-code model
using the qualified private settings copy; signed values remain negative in
the stored data. This table compares current magnitudes.

| ASD setting | Steady pairs | C5 model mean (A) | ASD bracket mean (A) | Mean C5 minus ASD (mA) |
| --- | --- | --- | --- | --- |
| 0.100 A | 10 | 0.101748 | 0.099950 | +1.798 |
| 0.500 A | 10 | 0.501102 | 0.499950 | +1.152 |
| 1.000 A | 10 | 0.999429 | 1.000000 | -0.571 |
| 0 A, 5 V maintained | 6 | 0 after stock deadband | 0.000000 | 0 after deadband |

No coefficients were fitted. These points support functional scaling on this
unit, not a traceable accuracy specification, full-range calibration or ADC
freshness/coherency qualification. The zero row uses the stock current deadband;
raw shunt samples are retained and must not be described as exactly zero.
CY scope values show differences from ASD, including a nonzero zero-load
current indication; CY analog calibration is unqualified here. Preserve its
waveforms as another observation, not an independently certified current standard.

Successful captures under `build/captures/`:

- `bench-20261117-131523-959255`: 0.1 A, 22,020 scope samples.
- `bench-20261117-131624-248310`: 0.5 A, 26,295 scope samples.
- `bench-20261117-131839-298778`: 1 A, 26,315 scope samples.
- `bench-20261117-132035-750657`: energized 0 A, 18,195 scope samples.

All decoded voltage requests in those sessions target Fixed 5 V. EPR capability
advertisements/5 V negotiation are not higher-voltage output requests. GUI
errors stayed 0, guard 9,448 bytes. Each session verified final LOAD OFF.
The aggregate report is
`build/gui-v0.1.5-cal-read/framework-bench-summary-20261117.json`.
Per-session `comparison-analysis-v2.json` separates steady/precheck phases.
ASD CSV mains values are CLI defaults, not measured/owner-confirmed test conditions.

## Failures and metadata limits retained

`bench-20261117-131227-251701` stopped before ASD connection because the wrapper
used an unsupported current-policy spelling. `bench-20261117-131341-630053`
retained ten real pairs and scope data, but the wrapper used a wrong status
attribute during completion checking. Its actual decoded OFF response is retained;
the original manifest remains incomplete. Regression checks now use the actual
CLI argument parser and status decoder, plus injected failures/bracketing.

The first two successful manifests hashed a buffered console log before its
final flush. All measurement/raw data hashes match; the console hash mismatch
is reported separately, and originals are retained. Later runs flush before
hashing and all recorded file hashes match. Do not silently replace original
manifests or mix preliminary combined precheck statistics with the v2 analysis.

## Reuse

Close competing instrument/HID clients, retain PD OFF on C5, and use the
qualified private ASD identity JSON. New directories refuse overwrite.

```powershell
cd D:\c5_standalone_rs
python -B tools\bench_compare.py --current 0.1 --seconds 10
python -B research\analyze_bench.py build\captures\<new-session>
```

Only verified COM3, Fixed 5 V, 0..1 A and 5..20-second holds are accepted by this
session-specific wrapper. The CLI's official PDO query is used and automatic
EPR reconciliation is disabled. There are no C5 Flash/sensor/storage-value writes.

## v0.1.6 shadow-cache extension and CY failure handling

Use `--shadow` with v0.1.6 to wait for a new sampler sequence for each bracket,
retaining sampler generations, cache age and GUI status. Sticky sampler faults
stop load; they are not automatically restarted. Lease-OFF can be restarted
explicitly by the host. Both sampler and ASD are stopped on exit. At 5 V,
0.1/1 A runs obtained ten steady pairs each, with model-minus-ASD mean current
magnitude differences +2.242/-0.313 mA. See the v0.1.6 physical aggregate report.

`bench-20261117-140549-334704` retained six energized-zero ASD/C5 pairs and
verified both stops, but CY returned failure and no usable scope stream. Its
manifest stays incomplete; partial validation is a separate file. A follow-up
STOP timed out despite USB enumeration. This generic CLI message cannot prove
Analyzer Utility contention; the underlying exception was USBErrorTimeout.
The owner reports prior intermittent CY unresponsiveness. After owner USB reset,
`cy-recovery-20261117-141202` captured 1,975 samples in 2 s and stopped/exported.
The bench guard now requires actual advancing EP83 samples as well as a recent
worker heartbeat, preventing idle USB responses from masquerading as live scope.

Host tool improvements after a firmware build are not part of its frozen image.
The verifier now checks/uses the associated source snapshot, if present; it
rejects a corrupt snapshot rather than silently substituting current sources.

## v0.1.8 gated bench adapter — 2026-11-17

`tools/bench_compare.py --gated --current 0.1 --seconds 10` selects the v0.1.8
cache. The adapter requires a newly published cache inside each ASD bracket and
its matching clear/set evidence sequence. Mismatched evidence is not accepted;
a fault aborts without automatic restart. A normal lease-OFF state can start a
new explicitly logged sampler generation. Final cleanup sends gated STOP and
records OFF separately from ASD LOAD OFF. Existing fixed-5 V / <=1 A bounds and
CY live-scope watchdog remain enforced. DIAG reads may clear status; no C5 sensor
configuration, storage-value or Flash writes are added. No GUI values enabled.

Four injected adapter tests plus ten existing bench checks passed. These are
host tests, not loaded hardware validation. The v0.1.8 package and its frozen
build sources are unchanged; this host-only extension is hashed in new bench
manifests. First physical step: normal-boot the already installed v0.1.8, restore
Framework -> Sumitomo 1.0 m -> CY4500-EPR -> C5 -> ASD-PD31, keep C5 PD OFF and
ASD LOAD OFF, then perform the bounded 5 V / 0.1 A comparison and verify OFF.

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
