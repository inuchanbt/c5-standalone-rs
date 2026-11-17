"""Read-only C5 GUI telemetry. Contains no DFU, flash, or PD commands."""
import argparse
import datetime as dt
import json
from pathlib import Path
import secrets
import struct
import time

MAGIC=b'C5G1'

def request(seq, nonce):
    if not 0 <= seq <= 0xffffffff or len(nonce) != 8: raise ValueError('Bad sequence/nonce')
    b=bytearray(64);b[:2]=b'\xff\x55';b[4]=128;b[8:10]=bytes([0x90,16])
    b[10:26]=MAGIC+struct.pack('<I',seq)+nonce
    b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
    return bytes(b)

def parse(raw, seq, nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([0x91,52]):raise ValueError('Not C5 GUI telemetry')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Checksum mismatch')
    p=raw[10:62]
    if p[:16]!=MAGIC+struct.pack('<I',seq)+nonce:raise ValueError('Stale sequence/nonce')
    state,keys,error,uptime,frames,lcd_ms,clock,guard,flags,gap,blocked=struct.unpack_from('<BBH8I',p,16)
    if state>3 or keys>15 or flags>>16>17:raise ValueError('Invalid telemetry values')
    return dict(state=['BOOT','INIT','GUI','ERROR'][state],keys=keys,error=error,uptime_ms=uptime,
        frames=frames,lcd_ms=lcd_ms,core_clock_hz=clock,unused_guard_bytes=guard,
        flipped=bool(flags&1),brightness_percent=(flags>>8)&255,page=flags>>16,
        max_button_poll_gap_ms=gap,blocked_actions=blocked)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=float,default=0)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.seconds<0:p.error('--seconds must be nonnegative')
    directory=Path(__file__).resolve().parents[1]/'build/captures'
    directory.mkdir(parents=True,exist_ok=True)
    output=a.output or directory/('gui-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'.jsonl')
    # Reserve the output before opening USB; never overwrite existing evidence.
    with output.open('x',encoding='utf8') as log:
        import hid
        candidates=hid.enumerate(0x0716,0x5053)
        if len(candidates)!=1 or candidates[0].get('serial_number')!='20211222':
            raise RuntimeError('Expected exactly the previously verified owner C5')
        device=hid.device();device.open_path(candidates[0]['path']);nonce=secrets.token_bytes(8)
        try:
            device.set_nonblocking(True)
            for _ in range(16):
                if not device.read(65):break
            else:raise RuntimeError('Continuous traffic; close the other HID client')
            device.set_nonblocking(False)
            started=time.monotonic();seq=0;last=None;then=started
            print('[MONITOR] C5 GUI status only. Ctrl+C stops monitoring.',flush=True)
            while not a.seconds or time.monotonic()-started<a.seconds:
                tx=request(seq,nonce)
                if device.write(b'\0'+tx)!=65:raise IOError('Short HID write')
                raw=bytes(device.read(65,2000))
                if not raw:raise TimeoutError('No GUI response; verify firmware, cable and mode. No retry.')
                status=parse(raw,seq,nonce);seq=(seq+1)&0xffffffff
                now=time.monotonic();fps=(status['frames']-last)/(now-then) if last is not None else 0
                row=dict(elapsed_s=round(now-started,3),fps=round(fps,2),**status)
                log.write(json.dumps(row)+'\n');log.flush()
                print(f"[{status['state']}] page={status['page']} keys=0x{status['keys']:x} fps={fps:.1f} lcd={status['lcd_ms']}ms guard={status['unused_guard_bytes']}B poll_gap_max={status['max_button_poll_gap_ms']}ms bright={status['brightness_percent']}% flip={status['flipped']}",flush=True)
                if status['error']:raise RuntimeError(f"C5 firmware error {status['error']}")
                last=status['frames'];then=now;time.sleep(1)
        except KeyboardInterrupt:print('[STOP] GUI continues running.',flush=True)
        finally:device.close();print('Capture:',output,flush=True)

if __name__=='__main__':main()
