# Workspace migration — 2026-11-17

The working root is `D:/c5_standalone_rs`, with `Cargo.toml` directly in that
directory. At the owner's explicit request, the old directory
`D:/doom_on_c5/c5-standalone-rs` was removed after full preservation and verification.
The surrounding DOOM project,
previous C5 research, backups and KWS-X1 source were not moved.

## Relocation completed — 2026-11-17

- The active v0.1.9 workspace was retained without overwriting newer files.
- All 2,942 legacy files (1,645,154,251 bytes), including `.git`, `target`,
  `.cache`, documents and firmware evidence, were copied into
  `build/migration-completion-20261117-161436/legacy-workspace/`.
  Empty directories were preserved too. Every source and archive file was
  checked against SHA-256 twice before removal; no reparse points were present.
- At the same relative paths in the active workspace, 628 files were identical,
  889 differed, and 1,425 legacy cache/build/Git files were absent. All legacy
  versions are retained in the archive; no missing non-cache project files
  needed merging into the active tree.
- The complete manifest and Git status snapshots are under
  `build/migration-completion-20261117-161436/`. This ignored archive is historical
  evidence, not a second development root, and may contain private owner data.
- The old subdirectory was removed with a checked absolute path. Other entries
  under `D:/doom_on_c5` were left intact. No hardware operations were performed.
- The destination write/read/delete probe succeeded. `build.ps1 --help` and
  `verify.ps1 --help` ran from the active root. Active scripts contain no old-root
  references. Frozen historical outputs were not rewritten.
- Both original v0.1 and current v0.1.9 packages retain their recorded digests.
  The v0.1.9 SHA-256 is
  `f05abfd3bfa141f498099c2d27dd9349c0ba49a61d34560581d0f0abcc9f830d`.

## Initial copy verification (historical)

- Git 2.54.0.windows.1 ran successfully. A uniquely named temporary file in the
  destination was created, read back byte-for-byte and removed successfully.
- The destination was empty before copying.
- All 255 copied files matched SHA-256, including hidden Git files, source,
  upstream snapshot, documents and build artifacts. Empty Git objects/refs
  directories were copied too; Git recognizes branch `c5/gui-bringup` with no
  commits and the same intent-to-add entries as the source.
- Creating the protected empty Git directories initially returned access denied;
  the authorized metadata copy succeeded with sandbox escalation. Other file
  copies and project writes succeeded without escalation.
- Root `target/` (about 1.63 GB) and `.cache/` were omitted as regenerable. A new
  project-local Cargo dependency cache was copied from the existing KWS-X1 cache
  without modifying that source. Build commands explicitly select the local copy.
- `build/migration-file-verification.json` records the pre-edit copied file
  hashes. Documentation path updates are subsequent, intentional differences.
- The GUI package SHA-256 remains
  `70f9045b16e96866541f3a3e7c27014c6ba008557802c091b2aa54b952f87e61`.

PowerShell printed a FileSystem provider initialization warning at process
startup. The successful file probe, hashes, Git commands and tests are direct
observations; that warning did not establish a project access failure.

## Script paths

`build.ps1`, `monitor.ps1` and `verify.ps1` use `$PSScriptRoot`. Their Python
entry points use `Path(__file__).resolve()` for the project root. No executable
path references the old working directory. The wrappers' Python executable,
Rust/LLVM toolchain, owner baseline and rollback paths still exist at their
original external locations. Those research/toolchain paths are intentional;
private baseline images are not copied into this project.

Use this from the new root to avoid Cargo writes in the KWS-X1 project:

```powershell
.\build.ps1 --host --cargo-home D:/c5_standalone_rs/.cache/cargo
.\build.ps1 --cargo-home D:/c5_standalone_rs/.cache/cargo
```

The current build script defaults to this project-local `.cache/cargo` path;
the explicit override above is also supported.

An ARM rebuild with the local cache succeeded but has a different package hash;
dependency source paths are embedded in both binaries and now name different
cache roots. Its package and complete generated build outputs are preserved in
`build/relocated-rebuild-20261117`. The hash-pinned imported candidate and its
matching manifest/raw/ELF/map/disassembly were restored at the original build
paths. At migration time, build commands overwrote those normal paths. The
subsequent v0.1.1 button correction changes the default output directory to
`build/gui-v0.1.1`, preserving the original migration artifacts. Check the
resulting manifest instead of assuming byte-identical reproduction.
See `docs/VALIDATION.md` for the separate rebuilt package digest.

## Initial physical status (historical)

`build/connection-enumeration-20261117.json` records zero matching C5 HID devices
inside the sandbox at 2026-11-17 09:43 JST. After the owner reported installation
and normal startup, sandbox enumeration still returned zero; host-access
enumeration detected one qualified device. The enumeration probes sent no device
requests. The subsequent read-only GUI monitor succeeded. See
`build/connection-host-after-user-boot-20261117.json` and
`docs/HARDWARE-VALIDATION.md`. The sandbox result alone does not establish that
the device was physically absent.

Subsequent v0.1.9 hardware, display and preservation checks are recorded in
`CHECKPOINT.md` and `docs/METER-DISPLAY.md`. Relocation does not require another
installation or hardware trial. The KWS-X1 flasher must never be used for the C5.
