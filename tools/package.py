"""C4/C5 package encoding. Pure offline logic; no device access."""
from functools import reduce
from operator import xor
import struct

FAMILY = bytes.fromhex('ef3d7b682c3b634d93b922b17b051a12')
DECODE = bytes.fromhex(
    '1ab6b7f17b8cd53c7c90d2f435f21be9db12775b3d7f3fbd2d472a50dcc3ff578283'
    '60fc9b4e88d0005f2e592bf9c638f0c88e8044fd737e0b2919afd89671b362e6e511'
    '919c4615c4c2a552b966acb22253ee54aab474cfb06c72a7925a56e785ecc19fce6ea'
    'e3b788f5d4be2640c4c1363c0414fbae41004a63e31e1b8486705d39869bf3665be06'
    '515cc78b0937c5a9a870d4871dda0df37630ad1794e0b114ed0e08429a33b555d9453'
    '9e37d4d01cb27ef256a3a7a796d164061a402ab860f346feb6bf728dea3cc752cca5e81'
    '0afa68f8070324cd1fa22f32439df5d7bc9ebb494ad68a84a121df97fe20d11e931c8d'
    'fb261895f6c9ddea9923e8a05889')
PACKAGE_BYTES = 0xe0000
PAYLOAD_BYTES = PACKAGE_BYTES - 48
APP_START = 0x08004000
ERASE_END = 0x080e4000
BOOT_SHA256 = 'aaf175a47bda0ad2f4a5b66f6759ac157b16fb4cccd565a13b63b0e182cab30d'

def decode(raw):
    data = raw.translate(DECODE)
    if len(data) != PACKAGE_BYTES or data[:7] != b'gzutapp' or data[20:36] != FAMILY:
        raise ValueError('Not the bounded C5 GUI package')
    payload = data[48:]
    if struct.unpack_from('<III', data, 36) != (len(payload), reduce(xor, payload, 0), sum(payload) & 0xffffffff):
        raise ValueError('Package checksum/length mismatch')
    return payload

def encode(raw):
    if not 0x1000 < len(raw) <= PAYLOAD_BYTES:
        raise ValueError('Application size out of bounds')
    payload = raw.ljust(PAYLOAD_BYTES, b'\xff')
    sp, reset = struct.unpack_from('<II', payload)
    if sp != 0x20017000 or not reset & 1 or not APP_START + 0x1000 <= reset < APP_START + len(raw):
        raise ValueError('Invalid application vectors')
    if payload[0x810:0x814] != b'C400' or payload[0xc00:0xc04] != b'\xff' * 4:
        raise ValueError('Bootloader tag/activation mismatch')
    if struct.unpack_from('<I', payload, 36 * 4)[0] != 0x080029ed:
        raise ValueError('Bootloader USB IRQ vector mismatch')
    header = bytearray(b'\xff' * 48)
    header[:7] = b'gzutapp'
    struct.pack_into('<HBB', header, 7, 2026, 11, 16)
    header[20:36] = FAMILY
    struct.pack_into('<III', header, 36, len(payload), reduce(xor, payload, 0), sum(payload) & 0xffffffff)
    result = (header + payload).translate(bytes(DECODE.index(i) for i in range(256)))
    if decode(result) != payload:
        raise ValueError('Package round trip failed')
    return result

def audit(actual, package, baseline):
    if len(actual) != 0x100000 or len(baseline) != 0x100000:
        raise ValueError('Two full 1 MiB images are required')
    payload = bytearray(decode(package))
    payload[0xc00] = 0xfe  # The single activation byte observed after official update.
    end = 0x4000 + len(payload)
    checks = {
        'application_matches_activated_package': actual[0x4000:end] == payload,
        'boot_and_factory_header_preserved': actual[:0x4000] == baseline[:0x4000],
        'erase_tail_is_ff': actual[end:0xe4000] == b'\xff' * 48,
        'after_erase_range_preserved': actual[0xe4000:] == baseline[0xe4000:],
    }
    return dict(checks, passed=all(checks.values()))
