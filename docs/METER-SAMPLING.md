# v0.1.6 raw shadow sampler

This candidate qualifies automatic acquisition separately from calibrated GUI
measurement. **Basic HID/load/lease tests and full internal-Flash audit now pass on the owner's unit.** The v0.1.5 manual/automated
load comparisons are recorded in CURRENT-COMPARISON.md and BENCH-AUTOMATION.md.

The host explicitly starts the sampler. Boot and normal GUI monitoring do not
start sensor reads. Each foreground step performs at most one bounded register
read, outside LCD scanout. After verifying INA228 IDs, each cycle brackets the
packed shunt/bus reads with CONFIG/ADC_CONFIG reads. Only the physically observed
`0000/FB68` configuration is supported; other settings stop acquisition rather
than being overwritten. IDs and registers are C5-specific, not KWS-X1 assumptions.

There are no register-value writes or DIAG_ALRT reads. TI documents flag/read
side effects in its [INA228 data sheet](https://www.ti.com/lit/ds/symlink/ina228.pdf),
sections 7.3 and 7.6. These remain outside the current raw diagnostic interface.
The cache timestamp is the completion time of host-side acquisition, **not an
ADC conversion timestamp**. A current cache never claims ADC freshness or an
atomic voltage/current frame. GUI, MAX, graph and energy inputs remain unavailable.

Bounds and failure policy:

- 12 ms per register transaction, 75 ms shunt/bus read span, 160 ms configuration
  bracket. Start another cycle no sooner than 200 ms after completion.
- A transport/configuration/data/window failure is sticky; no automatic retry
  or partial-sample publication. Restart requires another explicit start.
- A completed cache expires for current-use status after 500 ms. Preserve its
  raw values/counter for diagnostics, with current-use status false.
- Without host status/keepalive for more than 2,000 ms, sampling stops. Stop
  commands do not perform sensor/storage writes.
- Keep the foreground's existing GUI polling and stack-guard checks.

USB commands: `98/99` start/reply, `9A/9B` status/reply, `9C/9D` stop/reply,
magic `C5S1`, sequence and nonce echo. The reply includes sampler state, phase,
error, acquisition sequence/tick/age, raw shunt/bus, configuration and maximum
transaction/pair spans. `tools/shadow_monitor.py` validates the wire metadata,
records status plus GUI telemetry, stops on exit and verifies OFF. Do not run
the old raw bench collector concurrently with the shadow monitor.

```powershell
cd D:\c5_standalone_rs
.\shadow-monitor.ps1 --seconds 20
```

Host tests execute the production C scheduler, including LCD busy intervals,
NACK/deadline/shutdown/configuration-change faults, no partial publication,
lease expiry/restart, tick wrap and stale-cache claims. These are software
checks, not a measurement of physical sample cadence, button latency or stack peak.

Next hardware checks: boot candidate with side HID only; run shadow monitoring;
inspect advancing sample numbers, timing/window limits, errors, GUI frames,
buttons and guard; then qualify transitions at 5 V with the automated bench.
ADC freshness needs its own evidence before connecting measurements to GUI/MAX/
history/integration. Repeat full dual DFU installation/preservation audit.

## Dated physical observations

See `build/gui-v0.1.6-meter-shadow/hardware-validation-20261117.json`. HID-only
acquisition intervals were 305..313 ms, per-register maximum 4 ms, guard 9,376
bytes and GUI error 0. The lease test stopped without sampler requests after
three seconds and marked a 1,199 ms cache unusable. Separate 0.1/1 A shadow
comparisons completed; energized-zero ASD/C5 data were captured but CY failed,
so that combined run remains incomplete. Full dual Flash audit passed.

ADC conversion freshness is still unqualified; `docs/READY-FLAG-PROBE.md`
describes the next explicit flag-read experiment. Native firmware/package/source
snapshot remain unchanged by later host bench/verification tooling improvements.
