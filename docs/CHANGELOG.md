# Development milestones

These are local development candidates and observations, not GitHub release
announcements. See [STATUS.md](STATUS.md) for the current outcome. Historical
stage documents and frozen build manifests retain the status at recording time.

| Candidate | Change and observed outcome |
| --- | --- |
| v0.1 GUI-only | Ported upstream renderer/navigation, all pages/settings, proportional scanout, RAM brightness/rotation and unavailable measurements; host/link/package checks passed |
| v0.1.1 buttons | Corrected physical row to Back / Left(-) / OK / Right(+); owner confirmed mapping; dual-Flash audit passed |
| v0.1.2 meter-id | Read-only identity probe identified C5 INA228 |
| v0.1.3 meter-raw | Fixed raw register snapshots; 5 V/no-load KM003C comparison and dual-Flash audit recorded |
| v0.1.4 cal-read | External storage read experiment exposed LCD timeout during continuous diagnostics; incomplete 384-byte capture retained as a failure, not a completed backup |
| v0.1.5 cal-read | Deferred I²C diagnostic work outside scanout; equal ascending/descending 2 KiB captures, stock checksums, GUI health and dual-Flash audit passed; ASD/CY/C5 bench automation added |
| v0.1.6 meter-shadow | Automatic raw shadow sampling under a host lease; HID timing, expiry, load response and dual-Flash audit passed; one combined run remained incomplete when CY stopped responding |
| v0.1.7 ready-flag | Explicit conversion-ready clear/set experiment and dual-Flash audit passed |
| v0.1.8 meter-gated | Required observed clear->set before each cache publication; HID-only trial and fixed-5 V / 0, 0.1, 0.5, 1 A comparisons plus dual-Flash audit passed |
| v0.1.9 meter-display | Runtime-checked owner settings, autonomous gated samples, experimental Overview V/I/power/MAX; host, HID, paired loaded conversion, owner/panel and dual-Flash audit passed |

All physical observations apply to the owner's unit under the documented
conditions. Calibration provenance, wider-range accuracy and multi-unit
compatibility remain open. CY4500-EPR intermittent nonresponse was also reported
by the owner before this work; failed captures are retained and are not counted
as successful runs.

## Workspace relocation — 2026-11-17

Development now lives at `D:/c5_standalone_rs`, with `Cargo.toml` at the root.
The older `D:/doom_on_c5/c5-standalone-rs` was removed at the owner's request
after all 2,942 files were copied and SHA-256 verified. Its complete legacy
tree, including `.git`, `target` and `.cache`, remains in an ignored archive
under the current project's `build/`. The v0.1.9 working tree was retained;
DOOM and other research projects were left in place. [Migration record](MIGRATION.md).
