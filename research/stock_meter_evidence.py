"""Check fixed static landmarks in the owner's stock image; never opens USB."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=Path('D:/doom_on_km003c/local/c5-research/C4_C5_series_8.5.payload.bin')
EXPECTED='51d57d31a3d3b2fafbc18defcadeedf964bd418e0954543426ac6fc818e51682'
BASE=0x08004000

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--payload',type=Path,default=DEFAULT)
    p.add_argument('--output',type=Path,default=ROOT/'build/research/stock-v85-meter-evidence.json')
    a=p.parse_args();data=a.payload.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if digest!=EXPECTED:raise ValueError('This analysis is pinned to the inspected stock V8.5 payload')
    # Signatures check function entrypoints only; the interpretation below comes
    # from manual control-flow review of the corresponding ARM disassembly.
    entries={
        'check_226':(0x08007194,'10b5ff20'),
        'check_228':(0x080071f0,'10b53f20'),
        'check_ti_at_3e':(0x0800724c,'10b53e20'),
        'read_register_16':(0x0800b486,'70b50446'),
        'read_register_24':(0x0800b4c4,'70b50446'),
        'write_register_16_not_ported':(0x0800b506,'70b50c46'),
    }
    for address,signature in entries.values():
        expected=bytes.fromhex(signature)
        if data[address-BASE:address-BASE+len(expected)]!=expected:
            raise ValueError(f'Landmark mismatch: {address:#x}')
    literals={0x0800af24:0x40010c00,0x0800b05c:0x40010c00,0x0800b1a8:0x40010c00}
    for address,value in literals.items():
        if struct.unpack_from('<I',data,address-BASE)[0]!=value:
            raise ValueError(f'Literal mismatch: {address:#x}')
    report=dict(schema='c5-stock-v85-meter-static-evidence-v1',payload_sha256=digest,
        payload_bytes=len(data),static_analysis_only=True,device_io=False,
        checked_entrypoints={name:hex(value[0]) for name,value in entries.items()},
        checked_literals={hex(address):hex(value) for address,value in literals.items()},
        manual_findings=dict(register_address_7bit='0x40',scl_candidate='PB8',sda_candidate='PB9',
            ina228_check='register 0x3f shifted right by 4 equals 0x228',
            ina226_check='register 0xff shifted right by 4 equals 0x226',
            ti_manufacturer_check='register 0x3e equals 0x5449',
            selection_function='0x08007294',owner_unit_sensor_identified=False),
        datasheets=['https://www.ti.com/lit/ds/symlink/ina228.pdf',
                    'https://www.ti.com/lit/ds/symlink/ina226.pdf'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
