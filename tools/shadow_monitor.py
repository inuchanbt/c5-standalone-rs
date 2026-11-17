"""Start/status/stop the experimental raw cache; never promotes it to GUI data."""
import argparse
import datetime as dt
import json
from pathlib import Path
import struct
import time
from bench_compare import C5, ROOT
import monitor


def request(command, seq, nonce):
    if command not in (0x98,0x9a,0x9c):raise ValueError('Unknown shadow command')
    raw=bytearray(monitor.request(seq,nonce));raw[8]=command;raw[10:14]=b'C5S1'
    raw[62]=sum(raw[8:62])&255;raw[63]=sum(raw[:62])&255
    return bytes(raw)


def parse(command, raw, seq, nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([command+1,52]):
        raise ValueError('Not a shadow-cache reply')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Bad checksum')
    if raw[10:26]!=b'C5S1'+struct.pack('<I',seq)+nonce:raise ValueError('Stale reply')
    state,phase,error,flags,number,tick,age,shunt,bus,config,adc,max_step,max_pair,pair,cycle=struct.unpack_from('<4B5I6H',raw,26)
    if state>3 or phase>7 or flags&~7 or not flags&4:raise ValueError('Invalid shadow metadata')
    if flags&2 and (not flags&1 or not number or age>500 or state!=2):raise ValueError('False current-cache claim')
    return dict(state=['OFF','IDENTIFY','RUNNING','FAULT'][state],phase=phase,error=error,
        cache_available=bool(flags&1),cache_current=bool(flags&2),sample_number=number,
        acquisition_completed_tick=tick,cache_age_ms=age,shunt_raw=hex(shunt),bus_raw=hex(bus),
        config=hex(config),adc_config=hex(adc),max_transaction_ms=max_step,max_pair_span_ms=max_pair,
        last_pair_span_ms=pair,last_cycle_span_ms=cycle,freshness_qualified=False,gui_measurement_updates=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=float,default=20)
    a=p.parse_args()
    if not 2<=a.seconds<=60:p.error('Duration must be 2..60 seconds')
    out=ROOT/'build/captures'/('shadow-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    out.mkdir(parents=True,exist_ok=False);result=dict(complete=False,freshness_qualified=False)
    device=None;started=False
    with (out/'wire.jsonl').open('x',encoding='utf8') as wire,(out/'status.jsonl').open('x',encoding='utf8') as rows:
        try:
            device=C5(wire);result['gui_before']=device.gui()
            def exchange(command):
                return device.exchange(lambda seq,nonce:request(command,seq,nonce),
                                       lambda raw,seq,nonce:parse(command,raw,seq,nonce))
            started=True;result['start']=exchange(0x98)
            then=time.monotonic();numbers=set()
            while time.monotonic()-then<a.seconds:
                status=exchange(0x9a);gui=device.gui()
                rows.write(json.dumps(dict(elapsed_s=time.monotonic()-then,sampler=status,gui=gui))+'\n');rows.flush()
                if status['state']=='FAULT' or status['error']:raise RuntimeError('Shadow sampler fault: '+str(status))
                if status['cache_current']:numbers.add(status['sample_number'])
                time.sleep(.1)
            if len(numbers)<3:raise RuntimeError('Fewer than three new cache samples')
            result['distinct_samples']=len(numbers)
            result['complete']=True
        except Exception as error:result['error']=f'{type(error).__name__}: {error}'
        finally:
            if device is not None:
                try:
                    if started:
                        result['stop']=exchange(0x9c)
                        if result['stop']['state']!='OFF':raise RuntimeError('Sampler did not stop')
                    result['gui_after']=device.gui()
                except Exception as error:
                    result['complete']=False;result['cleanup_error']=f'{type(error).__name__}: {error}'
                device.device.close()
            (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2));print('Evidence:',out)
    return 0 if result['complete'] else 2


if __name__=='__main__':main()
