"""Observe an experimental clear/set-gated raw cache; GUI values stay disabled."""
import argparse
import datetime as dt
import json
import struct
import time
from bench_compare import C5, ROOT
import monitor


def request(command,seq,nonce):
    if command not in (0xa0,0xa2,0xa4,0xa6):raise ValueError('Unknown gated command')
    raw=bytearray(monitor.request(seq,nonce));raw[8]=command;raw[10:14]=b'C5N1'
    raw[62]=sum(raw[8:62])&255;raw[63]=sum(raw[:62])&255
    return bytes(raw)


def parse(command,raw,seq,nonce):
    if command not in (0xa0,0xa2,0xa4,0xa6):raise ValueError('Unknown gated command')
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([command+1,52]):
        raise ValueError('Not a gated-cache reply')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Bad checksum')
    if raw[10:26]!=b'C5N1'+struct.pack('<I',seq)+nonce:raise ValueError('Stale reply')
    if command==0xa6:
        number,clear,ready,reads,clears,sets,max_gate,cycle,diag=struct.unpack_from('<9I',raw,26)
        if diag>65535 or max_gate>1000 or cycle>1200:raise ValueError('Invalid gate evidence')
        return dict(sample_number=number,sample_clear_observed_tick=clear,sample_ready_observed_tick=ready,
            diag_read_count=reads,clear_event_count=clears,ready_event_count=sets,
            max_gate_wait_ms=max_gate,last_cycle_span_ms=cycle,last_diag=hex(diag))
    state,phase,error,flags,number,tick,age,shunt,bus,config,adc,step,pair,gate,cycle=struct.unpack_from('<4B5I6H',raw,26)
    if state>3 or phase>9 or flags&~15 or not flags&8:raise ValueError('Invalid gated metadata')
    if bool(flags&1)!=bool(number) or bool(flags&4)!=bool(number):raise ValueError('False completed-gate claim')
    if flags&2 and (not flags&1 or age>500 or state!=2 or error):raise ValueError('False current-cache claim')
    if number and (config or adc!=0xfb68 or gate>1000 or cycle>1200 or shunt&15 or bus&15):
        raise ValueError('Invalid published sample')
    if step>12 or pair>75:
        # A later failed transaction can legitimately increase the diagnostic
        # maximum after a previously published cache. Keep its raw error record.
        if state not in (0,3) or not error:raise ValueError('Invalid published sample')
    return dict(state=['OFF','IDENTIFY','RUNNING','FAULT'][state],phase=phase,error=error,
        cache_available=bool(flags&1),cache_current=bool(flags&2),completion_gate_observed=bool(flags&4),
        sample_number=number,acquisition_completed_tick=tick,cache_age_ms=age,
        shunt_raw=hex(shunt),bus_raw=hex(bus),config=hex(config),adc_config=hex(adc),
        max_transaction_ms=step,last_pair_span_ms=pair,last_gate_wait_ms=gate,last_cycle_span_ms=cycle,
        freshness_qualified=False,gui_measurement_updates=False,read_to_clear_side_effects_possible=True)


def validate_evidence(status,evidence):
    """Associate two RAM replies only if their publication sequence matches."""
    if status['sample_number']!=evidence['sample_number']:return False
    if not status['sample_number']:return True
    clear=evidence['sample_clear_observed_tick'];ready=evidence['sample_ready_observed_tick']
    if ((ready-clear)&0xffffffff)>500 or ((status['acquisition_completed_tick']-ready)&0xffffffff)>150:
        raise ValueError('Gate observation outside sample deadline')
    if evidence['ready_event_count']<status['sample_number'] or evidence['clear_event_count']<evidence['ready_event_count']:
        raise ValueError('Missing clear/set events')
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=float,default=20)
    a=p.parse_args()
    if not 2<=a.seconds<=60:p.error('Duration must be 2..60 seconds')
    out=ROOT/'build/captures'/('gated-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    out.mkdir(parents=True,exist_ok=False)
    result=dict(complete=False,freshness_qualified=False,gui_measurement_updates=False,
        sensor_value_writes=False,read_to_clear_side_effects_possible=True)
    device=None;started=False;numbers=set();associated=set()
    with (out/'wire.jsonl').open('x',encoding='utf8') as wire,(out/'status.jsonl').open('x',encoding='utf8') as rows:
        try:
            device=C5(wire);result['gui_before']=device.gui()
            def exchange(command):
                return device.exchange(lambda seq,nonce:request(command,seq,nonce),
                    lambda raw,seq,nonce:parse(command,raw,seq,nonce))
            started=True;result['start']=exchange(0xa0);then=time.monotonic()
            while time.monotonic()-then<a.seconds:
                status=exchange(0xa2);evidence=exchange(0xa6);gui=device.gui()
                matched=validate_evidence(status,evidence)
                rows.write(json.dumps(dict(elapsed_s=time.monotonic()-then,sampler=status,
                    gate_evidence=evidence,evidence_matches_sample=matched,gui=gui))+'\n');rows.flush()
                if status['state']=='FAULT' or status['error']:raise RuntimeError('Gated sampler fault: '+str(status))
                if gui['state']!='GUI' or gui['error']:raise RuntimeError('GUI fault: '+str(gui))
                if status['cache_current']:
                    numbers.add(status['sample_number'])
                    if matched:associated.add(status['sample_number'])
                time.sleep(.1)
            if len(associated)<3:raise RuntimeError('Fewer than three samples with associated gate evidence')
            result['complete']=True
        except Exception as error:result['error']=f'{type(error).__name__}: {error}'
        finally:
            result.update(distinct_samples=len(numbers),samples_with_associated_gate_evidence=len(associated))
            if device is not None:
                try:
                    if started:
                        result['stop']=exchange(0xa4)
                        if result['stop']['state']!='OFF':raise RuntimeError('Gated sampler did not stop')
                    result['gui_after']=device.gui()
                    if result['gui_after']['state']!='GUI' or result['gui_after']['error']:raise RuntimeError('Final GUI fault')
                except Exception as error:
                    result['complete']=False;result['cleanup_error']=f'{type(error).__name__}: {error}'
                device.device.close()
            (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2));print('Evidence:',out)
    return 0 if result['complete'] else 2


if __name__=='__main__':raise SystemExit(main())
