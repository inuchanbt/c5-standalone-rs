"""Offline reconstruction of stock V8.5 INA228 conversion inputs. Never opens USB.

Device settings and reconstructed samples are private research, not qualified
measurements. This does not implement sampling, filtering, calibration or writes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from storage_backup import settings_checks
from stock_meter_evidence import DEFAULT, EXPECTED, BASE


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def decode_settings(data):
    """Offsets used by 0801F11C/0801F1E8; neutral names avoid factory/user claims."""
    if len(data) != 2048 or not all(c['matches'] for c in settings_checks(data)):
        raise ValueError('Complete stock-checksummed settings required')
    values = {name: struct.unpack_from('<i', data, offset)[0] for name, offset in (
        ('voltage_span_delta_04', 0x04), ('current_zero_delta_08', 0x08),
        ('current_span_delta_0c', 0x0c), ('voltage_span_delta_4f', 0x4f),
        ('current_span_delta_53', 0x53))}
    for name, offset in [('voltage_reference_delta_10', 0x10),
                         ('current_reference_delta_14', 0x14)]:
        value = struct.unpack_from('<f', data, offset)[0]
        if not math.isfinite(value):
            raise ValueError('Nonfinite conversion field: ' + name)
        values[name] = value
    return values


def reconstruct(registers, fields):
    """Static stock-code model; sequential raw snapshots are not filtered frames."""
    config = int(registers['0x00'], 16)
    shunt = int(registers['0x04'], 16)
    bus = int(registers['0x05'], 16)
    if shunt & 15 or bus & 15 or shunt > 0xffffff or bus > 0xffffff:
        raise ValueError('Invalid INA228 packed sample')
    # 080071C8: (VBUS >> 2) & 0x003FFFFC.
    bus_input = (bus >> 2) & 0x003ffffc
    # 08007560: retain bits 22..4, sign-extend bit 23, then /4 in narrow range.
    shunt_input = shunt & 0x7ffff0
    if shunt & 0x800000:
        shunt_input -= 0x800000
    if config & 0x10:
        shunt_input >>= 2
    voltage_den = 204800 + fields['voltage_span_delta_04'] + fields['voltage_span_delta_4f']
    current_den = (409600 + fields['current_span_delta_0c'] +
                   fields['current_span_delta_53'] - fields['current_zero_delta_08'])
    for denominator in (voltage_den, current_den):
        if not 0 < denominator < 0x80000000:
            raise ValueError('Unqualified nonpositive/overflowing denominator')
    voltage = f32(f32(bus_input) * (10.0 + fields['voltage_reference_delta_10']) / f32(voltage_den))
    current = f32(f32(f32(shunt_input) - f32(fields['current_zero_delta_08'])) *
                  (2.0 + fields['current_reference_delta_14']) / f32(current_den))
    # Stock 0801F1AA uses the default kind-0 deadband, inclusive endpoints.
    if f32(-0.002) <= current <= f32(0.001):
        current = 0.0
    return dict(stock_model_voltage_V=voltage, stock_model_current_A=current,
                qualified_measurement=False, stock_filter_reproduced=False,
                freshness_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, type=Path)
    parser.add_argument('--raw-capture', type=Path)
    parser.add_argument('--stock', type=Path, default=DEFAULT)
    args = parser.parse_args()
    capture = args.capture.resolve()
    private_root = (ROOT / 'build/private-storage').resolve()
    if not capture.is_relative_to(private_root):
        raise ValueError('Private device analysis must stay under build/private-storage')
    manifest = json.loads((capture / 'manifest.json').read_text(encoding='utf8'))
    if not manifest.get('complete') or not manifest.get('two_passes_equal'):
        raise ValueError('Completed independent two-pass capture required')
    copies = [(capture / name).read_bytes() for name in ('storage-pass1.bin', 'storage-pass2.bin')]
    if len(copies[0]) != 2048 or copies[0] != copies[1]:
        raise ValueError('Full private copies differ')
    digest = hashlib.sha256(copies[0]).hexdigest()
    if any(p['sha256'] != digest for p in manifest['passes']) or len(manifest['passes']) != 2:
        raise ValueError('Capture hash mismatch')
    stock = args.stock.read_bytes()
    if hashlib.sha256(stock).hexdigest() != EXPECTED:
        raise ValueError('Stock V8.5 hash mismatch')
    def read(address, fmt):
        return struct.unpack_from('<' + fmt, stock, address - BASE)
    if read(0x080ae208, '4i') != (0, 204800, 0, 409600):
        raise ValueError('Stock kind-0 endpoint table mismatch')
    if read(0x0801f280, 'd') != (10.0,) or read(0x0801f1e0, 'd') != (2.0,):
        raise ValueError('Stock reference constant mismatch')
    fields = decode_settings(copies[0])
    report = dict(schema='c5-private-stock-conversion-research-v1',
        private_device_data=True, device_io=False, persistent_writes=False,
        stock_payload_sha256=EXPECTED, storage_sha256=digest,
        stock_settings_checks=settings_checks(copies[0]), conversion_fields=fields,
        calibration_qualified=False, gui_measurement_updates=False,
        limits=['Static stock-code reconstruction, not measured calibration accuracy',
                'Stock moving-average/filter pipeline is not reproduced',
                'No load/current-reference comparison or physical shunt identification',
                'Factory/user provenance of individual correction fields is not established'])
    if args.raw_capture:
        raw = json.loads(args.raw_capture.read_text(encoding='utf8'))
        if not raw.get('raw_samples'):
            raise ValueError('Expected raw sample capture')
        samples = []
        for sample in raw['raw_samples']:
            if sample['status'] != 'identified' or sample['model'] != 'INA228':
                raise ValueError('Unidentified/failed sample')
            samples.append(reconstruct(sample['raw_registers'], fields))
        report['raw_capture'] = str(args.raw_capture.resolve())
        report['stock_model_samples'] = samples
    output = capture / 'calibration-analysis.json'
    with output.open('x', encoding='utf8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print('Stock input pins, both private copies and four checksums verified.')
    print('Private offline analysis:', output)
    print('Calibration/current accuracy and freshness remain unqualified.')


if __name__ == '__main__':
    main()
