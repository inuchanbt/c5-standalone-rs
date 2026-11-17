"""Read the C5 internal 1 MiB flash twice using the verified command 10.

Pass 1 reads ascending addresses; pass 2 reads descending addresses. Only two
complete, byte-identical files are marked verified. This is not a restore test.
No device erase/program/reset/unlock commands are implemented.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time

import c5_probe as protocol

FLASH_BYTES = 1024 * 1024
CHUNK_BYTES = 32
REFERENCE_IMAGES = {
    "8.3": (718896, "d331b24ffdccee488691b657e46b5a962b2a65c8034a39052f35bb84310a1f04"),
    "8.5": (719100, "51d57d31a3d3b2fafbc18defcadeedf964bd418e0954543426ac6fc818e51682"),
}


def save_manifest(directory, manifest):
    temporary = directory / "manifest.json.tmp"
    with temporary.open("w", encoding="utf8") as out:
        json.dump(manifest, out, indent=2, ensure_ascii=False)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    temporary.replace(directory / "manifest.json")


def drain(device):
    # A queue is drained once before each uninterrupted pass, not before every
    # request. Only one request is outstanding, and every reply is validated.
    device.set_nonblocking(True)
    try:
        for _ in range(16):
            if not device.read(65):
                return
        raise RuntimeError("Unexpected continuously active HID input; verify DFU")
    finally:
        device.set_nonblocking(False)


def read_pass(device, directory, manifest, pass_number, *, size=FLASH_BYTES):
    if size <= 0 or size > FLASH_BYTES or size % CHUNK_BYTES:
        raise ValueError("Invalid flash-read length")
    name = f"flash-pass{pass_number}"
    partial = directory / (name + ".partial")
    final = directory / (name + ".bin")
    if final.exists():
        raise FileExistsError(final)
    record = {"pass": pass_number, "order": "ascending" if pass_number == 1 else "descending",
              "file": partial.name, "status": "reading", "bytes_read": 0}
    manifest["passes"].append(record)
    save_manifest(directory, manifest)
    offsets = range(0, size, CHUNK_BYTES) if pass_number == 1 else range(size - CHUNK_BYTES, -1, -CHUNK_BYTES)
    started = time.monotonic()
    drain(device)
    with partial.open("xb") as out:
        for offset in offsets:
            address = protocol.FLASH_START + offset
            trace = []
            try:
                data = protocol.read_chunk(device, address, CHUNK_BYTES, trace, drain_input=False)
            except BaseException:
                record["failed_address"] = f"0x{address:08x}"
                record["failed_exchange"] = trace
                raise
            out.seek(offset)
            out.write(data)
            record["bytes_read"] += len(data)
            record["last_address"] = f"0x{address:08x}"
            if record["bytes_read"] % 65536 == 0 or record["bytes_read"] == size:
                out.flush()
                os.fsync(out.fileno())
                elapsed = time.monotonic() - started
                record["elapsed_seconds"] = round(elapsed, 3)
                save_manifest(directory, manifest)
                speed = record["bytes_read"] / max(elapsed, 0.001)
                remaining = (size - record["bytes_read"]) / speed
                print(f"[PASS {pass_number}/2] {record['bytes_read'] / size:6.1%}  "
                      f"{record['bytes_read'] // 1024}/{size // 1024} KiB  "
                      f"{speed / 1024:.1f} KiB/s  ETA {remaining:.0f}s", flush=True)
        out.flush()
        os.fsync(out.fileno())
    raw = partial.read_bytes()
    if len(raw) != size:
        raise RuntimeError("Saved pass has an unexpected length")
    record.update(status="complete_unverified", bytes_on_disk=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    partial.rename(final)
    record["file"] = final.name
    save_manifest(directory, manifest)
    return raw


def load_proof(path):
    proof = json.loads(path.read_text(encoding="utf8"))
    if proof.get("schema") != "witrn-c5-read-probe-v1" or proof.get("status") != "read_complete_not_a_full_backup":
        raise ValueError("A successful C5 stage-1 probe JSON is required")
    if len(proof.get("devices", [])) != 1:
        raise ValueError("The probe must identify exactly one device")
    for name, (address, length) in protocol.REGIONS.items():
        region = proof["regions"][name]
        if int(region["address"], 16) != address or len(bytes.fromhex(region["hex"])) != length:
            raise ValueError("Unexpected region in probe JSON")
    return proof


def execute(args, hid_module, proof):
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "witrn-c5-double-flash-backup-v1",
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "starting", "flash_base": hex(protocol.FLASH_START),
        "flash_bytes": FLASH_BYTES, "read_command": 10,
        "programming_commands_implemented": False, "restore_tested": False,
        "probe_json": str(args.probe_json.resolve()), "passes": [],
    }
    save_manifest(directory, manifest)
    device = None
    try:
        candidates = hid_module.enumerate(protocol.VID, protocol.PID)
        if args.path_hex:
            candidates = [d for d in candidates if d["path"].hex() == args.path_hex.lower()]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one C4/C5 HID path, found {len(candidates)}")
        actual = protocol.json_device(candidates[0])
        previous = proof["devices"][0]
        for key in ("vendor_id", "product_id", "serial_number", "release_number", "product_string", "interface_number"):
            if actual.get(key) != previous.get(key):
                raise RuntimeError(f"Device {key} differs from successful probe")
        manifest["device"] = actual
        device = hid_module.device()
        device.open_path(candidates[0]["path"])
        drain(device)
        manifest["preflight_requests"] = []
        for name, (address, length) in protocol.REGIONS.items():
            data = b"".join(protocol.read_chunk(device, address + off, min(32, length - off),
                           manifest["preflight_requests"], drain_input=False) for off in range(0, length, 32))
            if data.hex() != proof["regions"][name]["hex"]:
                raise RuntimeError(f"Preflight {name} differs from the successful probe; stopped")
        manifest["status"] = "reading"
        save_manifest(directory, manifest)
        print("[OK] Device and 384-byte preflight match the successful probe.", flush=True)
        first = read_pass(device, directory, manifest, 1)
        second = read_pass(device, directory, manifest, 2)
        if first != second:
            first_difference = next(i for i, (a, b) in enumerate(zip(first, second)) if a != b)
            manifest["first_difference_address"] = hex(protocol.FLASH_START + first_difference)
            raise RuntimeError("Two complete reads differ; files retained, backup NOT verified")
        # Explicit checks against preflight guard against a consistent misplaced
        # or shifted stream being labelled a good backup.
        for name, (address, length) in protocol.REGIONS.items():
            offset = address - protocol.FLASH_START
            if first[offset:offset + length].hex() != proof["regions"][name]["hex"]:
                raise RuntimeError(f"Full backup does not match preflight region {name}")
        sp, reset = struct.unpack_from("<II", first, 0x4000)
        manifest["app_vectors"] = {"initial_sp": hex(sp), "reset_vector": hex(reset)}
        manifest["stock_payload_comparison"] = {}
        for version, (length, expected) in REFERENCE_IMAGES.items():
            digest = hashlib.sha256(first[0x4000:0x4000 + length]).hexdigest()
            manifest["stock_payload_comparison"][version] = {
                "bytes": length, "sha256": digest, "expected_sha256": expected, "exact_match": digest == expected}
        for record in manifest["passes"]:
            record["status"] = "verified_identical"
        manifest.update(status="verified_identical", sha256=hashlib.sha256(first).hexdigest(),
                        completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        save_manifest(directory, manifest)
        print(f"[VERIFIED] Two identical {FLASH_BYTES}-byte flash reads.", flush=True)
        print(f"SHA256: {manifest['sha256']}", flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        manifest["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        save_manifest(directory, manifest)
        print(f"[STOPPED] {manifest['error']}", file=sys.stderr, flush=True)
        return 3
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass
        print(f"Manifest: {directory / 'manifest.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dfu", action="store_true", help="DFU is visible on the C5 screen")
    parser.add_argument("--probe-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New backup directory, must not exist")
    parser.add_argument("--path-hex", help="Exact HID path if multiple devices are present")
    args = parser.parse_args()
    if not args.dfu:
        parser.error("--dfu is required; keep the C5 in DFU mode")
    if args.output_dir.exists():
        parser.error("Output directory already exists; choose a new one")
    try:
        proof = load_proof(args.probe_json)
        import hid
    except (OSError, ValueError, KeyError, ImportError) as exc:
        parser.error(str(exc))
    return execute(args, hid, proof)


if __name__ == "__main__":
    raise SystemExit(main())
