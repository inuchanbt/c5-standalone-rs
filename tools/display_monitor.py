"""Read experimental GUI conversion telemetry; optionally stop acquisition."""
import argparse,datetime as dt,json,struct,time
from bench_compare import C5,ROOT
import monitor,gated_monitor

def request(seq,nonce):
    b=bytearray(monitor.request(seq,nonce));b[8]=0xa8;b[10:14]=b'C5V1'
    b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
    return bytes(b)

def parse(raw,seq,nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([0xa9,52]):raise ValueError('Wrong display reply')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Bad checksum')
    if raw[10:26]!=b'C5V1'+struct.pack('<I',seq)+nonce:raise ValueError('Stale reply')
    settings,error,enabled,valid,mv,ma,number,age,conversion_error=struct.unpack_from('<5Ii3I',raw,26)
    if settings>2 or enabled>1 or valid>1 or conversion_error>1:raise ValueError('Invalid metadata')
    if valid and (settings!=1 or error or conversion_error or not number or age>500 or mv>5500 or abs(ma)>1100):
        raise ValueError('Invalid live reading')
    return dict(settings_state=['READING','READY','FAULT'][settings],settings_error=error,
        autonomous_enabled=bool(enabled),reading_valid=bool(valid),voltage_mV=mv,current_mA=ma,
        sample_number=number,age_ms=age,conversion_error=bool(conversion_error))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=float,default=20)
    p.add_argument('--stop',action='store_true');a=p.parse_args()
    if not 2<=a.seconds<=60:p.error('Duration must be 2..60 seconds')
    out=ROOT/'build/captures'/('display-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir(parents=True,exist_ok=False)
    r=dict(complete=False,experimental=True);device=None
    with (out/'wire.jsonl').open('x',encoding='utf8') as wire,(out/'status.jsonl').open('x',encoding='utf8') as rows:
        try:
            device=C5(wire);r['gui_before']=device.gui();start=time.monotonic();numbers=set()
            while time.monotonic()-start<a.seconds:
                d=device.exchange(request,parse);g=device.gui();rows.write(json.dumps(dict(display=d,gui=g))+'\n');rows.flush()
                if d['settings_error'] or d['conversion_error']:raise RuntimeError('Meter fault: '+str(d))
                if d['reading_valid']:numbers.add(d['sample_number'])
                time.sleep(.1)
            if len(numbers)<3:raise RuntimeError('Fewer than three GUI samples')
            r['distinct_samples']=len(numbers);r['gui_after']=device.gui();r['complete']=True
        except Exception as e:r['error']=f'{type(e).__name__}: {e}'
        finally:
            if device:
                try:
                    if a.stop:
                        r['stop']=device.exchange(lambda s,n:gated_monitor.request(0xa4,s,n),lambda b,s,n:gated_monitor.parse(0xa4,b,s,n))
                        time.sleep(.1);r['display_after_stop']=device.exchange(request,parse)
                        if r['stop']['state']!='OFF' or r['display_after_stop']['reading_valid']:raise RuntimeError('Stop did not invalidate GUI')
                except Exception as e:r['complete']=False;r['cleanup_error']=str(e)
                device.device.close()
            (out/'manifest.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print(json.dumps(r,indent=2));print('Evidence:',out)
    return 0 if r['complete'] else 2
if __name__=='__main__':raise SystemExit(main())
