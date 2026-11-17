"""One explicit C5 meter-ID probe. No sensor-value writes, scanning or PD commands."""
import argparse
import datetime as dt
import json
from pathlib import Path
import secrets
import struct
import monitor

MAGIC=b'C5M1'
STATUS=['identified','unknown_identity','nack','bus_busy','timeout','gui_not_ready']

def request(seq,nonce):
    b=bytearray(monitor.request(seq,nonce));b[8]=0x92;b[10:14]=MAGIC
    b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
    return bytes(b)

def parse(raw,seq,nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([0x93,36]):
        raise ValueError('Not a C5 meter-ID response')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:
        raise ValueError('Checksum mismatch')
    if raw[10:26]!=MAGIC+struct.pack('<I',seq)+nonce:raise ValueError('Stale sequence/nonce')
    status,kind,lines,valid,m3e,d3f,mfe,dff,elapsed,stage,reads=struct.unpack_from('<4B4HI2H',raw,26)
    if status>=len(STATUS) or kind>2 or lines>3 or valid>15 or reads!=valid.bit_count():
        raise ValueError('Invalid meter-ID metadata')
    if status==0:
        if kind==1:identity=valid&12==12 and mfe==0x5449 and dff>>4==0x226
        elif kind==2:identity=valid&3==3 and m3e==0x5449 and d3f>>4==0x228
        else:identity=False
        if not identity:raise ValueError('Model label disagrees with raw ID registers')
    elif kind!=0:raise ValueError('Failed/unknown probe must not label a sensor')
    values={f'0x{register:02x}':f'0x{value:04x}' if valid&(1<<index) else None
            for index,(register,value) in enumerate([(0x3e,m3e),(0x3f,d3f),(0xfe,mfe),(0xff,dff)])}
    return dict(status=STATUS[status],model=['unknown','INA226','INA228'][kind],
                i2c_address='0x40',idle_scl=bool(lines&1),idle_sda=bool(lines&2),
                id_registers=values,elapsed_ms=elapsed,successful_reads=reads,
                failed_register=f'0x{stage>>8:02x}' if stage else None,
                failed_phase=stage&255 if stage else None)

def raw_request(seq,nonce):
    b=bytearray(request(seq,nonce));b[8]=0x94;b[12]=ord('R')
    b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255;return bytes(b)

def parse_raw(raw,seq,nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([0x95,52]):
        raise ValueError('Not a C5 raw meter response')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Checksum mismatch')
    if raw[10:26]!=b'C5R1'+struct.pack('<I',seq)+nonce:raise ValueError('Stale sequence/nonce')
    status,kind,lines,reserved,valid,config,adc,cal,tempco,temp,shunt,bus,elapsed,stage,reads=struct.unpack_from('<4B6H5I',raw,26)
    if status>6 or kind>2 or lines>3 or reserved or valid>127 or shunt>0xffffff or bus>0xffffff:
        raise ValueError('Invalid raw diagnostic metadata')
    if status==0 and (kind!=2 or valid!=127 or reads!=9):raise ValueError('Incomplete raw success')
    if valid and (kind!=2 or reads!=valid.bit_count()+2):raise ValueError('Raw data without verified identity')
    values=[config,adc,cal,tempco,shunt,bus,temp]
    registers={f'0x{reg:02x}':f'0x{value:0{6 if reg in (4,5) else 4}x}' if valid&(1<<reg) else None
               for reg,value in enumerate(values)}
    return dict(status=(STATUS+['unsupported_model'])[status],model=['unknown','INA226','INA228'][kind],
        raw_registers=registers,elapsed_ms=elapsed,successful_reads=reads,
        failed_register=f'0x{stage>>8:02x}' if stage else None,failed_phase=stage&255 if stage else None,
        calibrated=False,freshness_qualified=False,gui_measurement_updates=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--raw',action='store_true',help='Also read INA228 registers 0x00..0x06 without configuration writes')
    parser.add_argument('--samples',type=int,default=1,help='Raw snapshots, 1..10; requires --raw when above 1')
    a=parser.parse_args()
    if not 1<=a.samples<=10 or (a.samples!=1 and not a.raw):parser.error('--samples must be 1..10 and requires --raw above 1')
    directory=Path(__file__).resolve().parents[1]/'build/captures'
    output=a.output or directory/('meter-id-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(schema='c5-meter-id-probe-v1',utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                sensor_register_value_writes=False,flash_writes=False,pd_commands=False,requests=[])
    device=None;exit_code=2
    with output.open('x',encoding='utf8') as stream:
        try:
            import hid
            candidates=hid.enumerate(0x0716,0x5053)
            if len(candidates)!=1 or candidates[0].get('serial_number')!='20211222':
                raise RuntimeError('Expected exactly the previously verified owner C5')
            device=hid.device();device.open_path(candidates[0]['path']);device.set_nonblocking(True)
            for _ in range(16):
                if not device.read(65):break
            else:raise RuntimeError('Continuous traffic; close the other HID client')
            device.set_nonblocking(False);nonce=secrets.token_bytes(8)
            def exchange(tx):
                entry=dict(tx=tx.hex());report['requests'].append(entry)
                if device.write(b'\0'+tx)!=65:raise IOError('Short HID write')
                raw=bytes(device.read(65,2000));entry['rx']=raw.hex()
                if not raw:raise TimeoutError('No response. No retry; check firmware and mode.')
                return raw
            report['gui_before']=monitor.parse(exchange(monitor.request(0,nonce)),0,nonce)
            if report['gui_before']['state']!='GUI' or report['gui_before']['error']:
                raise RuntimeError('GUI is not healthy; no meter-ID request sent')
            report['meter']=parse(exchange(request(1,nonce)),1,nonce)
            seq=2
            if a.raw and report['meter']['status']=='identified' and report['meter']['model']=='INA228':
                report['raw_samples']=[]
                for _ in range(a.samples):
                    snapshot=parse_raw(exchange(raw_request(seq,nonce)),seq,nonce);seq+=1
                    report['raw_samples'].append(snapshot)
                    if snapshot['status']!='identified':break
                    if len(report['raw_samples'])<a.samples:
                        import time
                        time.sleep(0.5)
            report['gui_after']=monitor.parse(exchange(monitor.request(seq,nonce)),seq,nonce)
            if report['gui_after']['state']!='GUI' or report['gui_after']['error']:
                raise RuntimeError('GUI error after meter-ID request')
            exit_code=0 if report['meter']['status']=='identified' else 2
            if a.raw and (not report.get('raw_samples') or any(s['status']!='identified' for s in report['raw_samples'])):exit_code=2
        except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
        finally:
            if device is not None:device.close()
            json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report,indent=2));print('Evidence:',output)
    return exit_code

if __name__=='__main__':raise SystemExit(main())
