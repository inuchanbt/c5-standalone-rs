"""Explicit eight-read INA228 DIAG_ALRT experiment. Reads can clear latched flags."""
import argparse
import datetime as dt
import json
import struct
import time
from bench_compare import C5, ROOT
import monitor

STATUSES=['ok','unknown','nack','bus_busy','timeout','gui_not_ready','unsupported_configuration_or_model']


def request(seq,nonce):
    data=bytearray(monitor.request(seq,nonce));data[8]=0x9e;data[10:14]=b'C5F1'
    data[62]=sum(data[8:62])&255;data[63]=sum(data[:62])&255
    return bytes(data)


def parse(raw,seq,nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([0x9f,52]):raise ValueError('Not a flag-probe response')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Bad checksum')
    if raw[10:26]!=b'C5F1'+struct.pack('<I',seq)+nonce:raise ValueError('Stale reply')
    status,kind,lines,count,config,adc,mfg,die,*tail=struct.unpack_from('<4B4H8H2I',raw,26)
    if status>=len(STATUSES) or kind>2 or lines>3 or count>8:raise ValueError('Invalid flag metadata')
    if status==0 and (kind!=2 or lines!=3 or count!=8 or mfg!=0x5449 or die>>4!=0x228 or config!=0 or adc!=0xfb68):
        raise ValueError('Incomplete or unqualified success')
    diag=tail[:count];elapsed,stage=tail[8:]
    if status==0 and stage:raise ValueError('Failure stage on successful reply')
    return dict(status=STATUSES[status],kind=kind,config=hex(config),adc_config=hex(adc),
        manufacturer_id=hex(mfg),device_id=hex(die),diag_hex=[hex(x) for x in diag],
        conversion_ready=[bool(x&2) for x in diag],memory_ok=[bool(x&1) for x in diag],
        alert_latched=[bool(x&0x8000) for x in diag],elapsed_ms=elapsed,failed_stage=stage,
        sensor_value_writes=False,read_to_clear_side_effects_possible=True,freshness_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--samples',type=int,default=5);a=p.parse_args()
    if not 1<=a.samples<=10:p.error('Only 1..10 explicit probes are allowed')
    out=ROOT/'build/captures'/('fresh-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    out.mkdir(parents=True,exist_ok=False);device=None;report=dict(complete=False,probes=[],sensor_value_writes=False,
        read_to_clear_side_effects_possible=True,freshness_qualified=False)
    with (out/'wire.jsonl').open('x',encoding='utf8') as trace:
        try:
            device=C5(trace);report['gui_before']=device.gui()
            for n in range(a.samples):
                value=device.exchange(request,parse);report['probes'].append(value)
                if value['status']!='ok':raise RuntimeError('Flag probe failed; no retry')
                if n+1<a.samples:time.sleep(.5)
            report['gui_after']=device.gui();report['complete']=True
        except Exception as error:report['error']=f'{type(error).__name__}: {error}'
        finally:
            if device is not None:device.device.close()
            (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2));print('Evidence:',out)
    return 0 if report['complete'] else 2


if __name__=='__main__':main()
