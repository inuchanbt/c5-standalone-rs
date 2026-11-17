"""WITRN C4/C5 DFU investigation: enumeration and bounded flash reads only.

No erase, program, reset, unlock, or application-jump commands are implemented.
The read protocol is recovered from the owner's WITRN_UP_V30 updater. Command 10
was verified on the owner's DFU device on 2026-11-16 (384 bytes, 12 replies).
Use --read-info only with DFU visible on the C5.
Requires Python 3.10+ and the 'hidapi' package (import name: hid).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import struct
import sys
import time

VID, PID = 0x0716, 0x5053
READ_COMMAND = 0x0A
FLASH_START, FLASH_END = 0x08000000, 0x08100000
REGIONS = {
    "boot_version": (0x08001400, 256),
    "factory_header": (0x08003800, 64),
    "app_vectors": (0x08004000, 64),
}


def build_read_request(address: int, count: int, ticks: int) -> bytes:
    if not 1 <= count <= 32:
        raise ValueError("Only 1..32-byte reads are allowed")
    if not FLASH_START <= address < address + count <= FLASH_END:
        raise ValueError("Read outside the C5 internal flash range")
    ticks &= 0xFFFFFFFF
    frame = bytearray(64)
    frame[:8] = bytes((0xFF, 0x55, (ticks // 1000) & 255,
                      (ticks % 1000) & 255, ((ticks // 30) | 128) & 255,
                      (ticks // 100) & 255, ticks % 100, (ticks // 80) & 255))
    frame[8:10] = bytes((READ_COMMAND, 5))
    struct.pack_into("<IB", frame, 10, address, count)
    frame[62] = sum(frame[8:62]) & 255
    # The outer checksum excludes the inner checksum byte at offset 62.
    frame[63] = sum(frame[:62]) & 255
    return bytes(frame)


def parse_reply(raw: bytes, expected_count: int) -> bytes:
    # hidapi normally removes the zero report ID on input. Accept an explicit
    # leading zero too, without accepting arbitrary prefixes or truncated data.
    if len(raw) == 65 and raw[0] == 0:
        raw = raw[1:]
    if len(raw) != 64 or raw[:2] != b"\xff\x55":
        raise ValueError("Unexpected HID frame length or magic")
    if raw[62] != sum(raw[8:62]) & 255:
        raise ValueError("Inner checksum mismatch")
    if raw[63] != sum(raw[:62]) & 255:
        raise ValueError("Outer checksum mismatch")
    if raw[8] != READ_COMMAND:
        raise ValueError(f"Unexpected reply command 0x{raw[8]:02x}")
    if raw[9] != expected_count:
        raise ValueError(f"Reply length {raw[9]} does not match {expected_count}")
    return raw[10:10 + expected_count]


def json_device(device: dict) -> dict:
    return {k: v.hex() if isinstance(v, bytes) else v for k, v in device.items()}


def read_chunk(device, address: int, count: int, trace: list, *, drain_input: bool = True) -> bytes:
    # Drain stale reports before every request; no speculative retries.
    if drain_input:
        for _ in range(16):
            stale = device.read(65, 5)
            if not stale:
                break
            trace.append({"discarded_rx": bytes(stale).hex()})
        else:
            raise RuntimeError("Input is continuously active; stop and verify DFU mode")
    request = build_read_request(address, count, int(time.monotonic() * 1000))
    trace.append({"address": f"0x{address:08x}", "count": count, "tx": request.hex()})
    written = device.write(b"\0" + request)
    if written != 65:
        raise RuntimeError(f"Short HID write: {written}/65")
    reply = bytes(device.read(65, 1500))
    trace[-1]["rx"] = reply.hex()
    if not reply:
        raise TimeoutError("No response to the read request; no further commands sent")
    return parse_reply(reply, count)


def run(args, hid_module) -> tuple[dict, int]:
    candidates = hid_module.enumerate(VID, PID)
    report = {
        "schema": "witrn-c5-read-probe-v1",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "device_programming_commands_implemented": False,
        "hardware_protocol_previously_verified": True,
        "devices": [json_device(d) for d in candidates],
        "requests": [], "regions": {},
    }
    if not args.read_info:
        report["status"] = "enumerated" if candidates else "no_matching_device"
        return report, 0 if candidates else 2
    if not args.dfu:
        raise ValueError("--read-info requires --dfu and DFU visible on the C5")
    selected = candidates
    if args.path_hex:
        selected = [d for d in candidates if d["path"].hex() == args.path_hex.lower()]
    if len(selected) != 1:
        report["status"] = "no_matching_device" if not selected else "ambiguous_device"
        return report, 2
    device = hid_module.device()
    try:
        device.open_path(selected[0]["path"])
        for name, (start, size) in REGIONS.items():
            data = bytearray()
            for offset in range(0, size, 32):
                data += read_chunk(device, start + offset, min(32, size - offset), report["requests"])
            report["regions"][name] = {"address": f"0x{start:08x}", "hex": data.hex()}
        vectors = bytes.fromhex(report["regions"]["app_vectors"]["hex"])
        sp, reset = struct.unpack_from("<II", vectors)
        report["app_vectors"] = {"initial_sp": hex(sp), "reset_vector": hex(reset)}
        report["boot_version_strings"] = [part.decode("utf8", errors="replace") for part in
            bytes.fromhex(report["regions"]["boot_version"]["hex"]).split(b"\0")[:3]]
        report["status"] = "read_complete_not_a_full_backup"
        return report, 0
    except Exception as exc:
        report["status"] = "read_failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        return report, 3
    finally:
        device.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-info", action="store_true", help="Read 384 bytes of fixed flash regions")
    parser.add_argument("--dfu", action="store_true", help="Assert DFU is visible on the C5 screen")
    parser.add_argument("--path-hex", help="Select one exact path from an enumeration result")
    parser.add_argument("--output", type=Path, help="New JSON file; existing files are never replaced")
    args = parser.parse_args()
    if args.read_info and not args.dfu:
        parser.error("--read-info requires --dfu and DFU visible on the C5")
    if args.output and args.output.exists():
        parser.error("Output already exists; choose a new filename")
    try:
        import hid
    except ImportError:
        print("Install dependency with: python -m pip install hidapi", file=sys.stderr)
        return 4
    report, status = run(args, hid)
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf8") as stream:
            stream.write(encoded + "\n")
    print(encoded)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
