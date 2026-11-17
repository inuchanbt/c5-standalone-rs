"""Read the stock-addressed external 2 KiB twice. No persistent writes or init tests."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import secrets
import struct
import monitor
import probe_meter

MAGIC=b'C5E1'
STATUSES=['ok','unknown','nack','bus_busy','timeout','gui_not_ready','unsupported_model','invalid_block']

def request(block,nonce):
    if not 0<=block<128:raise ValueError('Only fixed 16-byte blocks in the stock 2 KiB range are allowed')
    b=bytearray(monitor.request(block,nonce));b[8]=0x96;b[10:14]=MAGIC
    b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255;return bytes(b)

def parse(raw,block,nonce):
    if len(raw)==65 and raw[0]==0:raw=raw[1:]
    if len(raw)!=64 or raw[:2]!=b'\xff\x55' or raw[8:10]!=bytes([0x97,44]):
        raise ValueError('Not a C5 fixed storage-read response')
    if raw[62]!=sum(raw[8:62])&255 or raw[63]!=sum(raw[:62])&255:raise ValueError('Checksum mismatch')
    if raw[10:26]!=MAGIC+struct.pack('<I',block)+nonce:raise ValueError('Stale block/nonce')
    status,count,lines,reserved,offset,stage,elapsed,data=struct.unpack_from('<4BHHI16s',raw,26)
    if status>=len(STATUSES) or count>16 or lines>3 or reserved:raise ValueError('Invalid storage metadata')
    if status not in (5,7) and offset!=block*16:raise ValueError('Wrong storage address')
    if status==0 and (count!=16 or lines!=3 or stage):raise ValueError('Incomplete storage success')
    return dict(status=STATUSES[status],count=count,offset=offset,elapsed_ms=elapsed,
        idle_scl=bool(lines&1),idle_sda=bool(lines&2),failed_stage=stage,data_hex=data[:count].hex())

def settings_checks(data):
    if len(data)!=2048:raise ValueError('Expected two complete KiB')
    # Stock V8.5 checks at B54C/B5A0/B584/B564 use XOR(data) ^ A5.
    checks=[]
    for start,end in [(0,0x1b),(0x1c,0x6f),(0x70,0x9f),(0xa0,0xe9)]:
        computed=0xa5
        for value in data[start:end]:computed^=value
        checks.append(dict(start=hex(start),checksum_offset=hex(end),stored=data[end],
                           computed=computed,matches=data[end]==computed))
    return checks

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    out=a.output_dir or root/'build/private-storage'/('read-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
    out.mkdir(parents=True,exist_ok=False)
    manifest=dict(schema='c5-external-storage-dual-read-v1',utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  private_device_data=True,persistent_writes=False,stock_storage_init_called=False,
                  range_bytes=2048,block_bytes=16,passes=[],complete=False)
    device=None;status=2
    with (out/'wire-trace.jsonl').open('x',encoding='utf8') as trace:
        try:
            import hid
            devices=hid.enumerate(0x0716,0x5053)
            if len(devices)!=1 or devices[0].get('serial_number')!='20211222':
                raise RuntimeError('Expected exactly the previously qualified owner C5')
            device=hid.device();device.open_path(devices[0]['path']);device.set_nonblocking(True)
            for _ in range(16):
                if not device.read(65):break
            else:raise RuntimeError('Continuous traffic; close the other HID client')
            device.set_nonblocking(False)
            def exchange(tx,pass_number=0):
                entry=dict(pass_number=pass_number,tx=tx.hex())
                try:
                    if device.write(b'\0'+tx)!=65:raise IOError('Short HID write')
                    raw=bytes(device.read(65,2000));entry['rx']=raw.hex()
                    if not raw:raise TimeoutError('No response; no retry')
                    return raw
                finally:trace.write(json.dumps(entry)+'\n');trace.flush()
            nonce=secrets.token_bytes(8)
            before=monitor.parse(exchange(monitor.request(0,nonce)),0,nonce)
            manifest['gui_before']=before
            if before['state']!='GUI' or before['error']:raise RuntimeError('GUI not healthy; no storage read sent')
            identity=probe_meter.parse(exchange(probe_meter.request(1,nonce)),1,nonce)
            manifest['meter_identity']=identity
            if identity['status']!='identified':raise RuntimeError('Owner meter identity not confirmed')
            for number in (1,2):
                # A fresh nonce for EACH pass prevents a pass-1 response from
                # satisfying a pass-2 read of the same fixed block number.
                nonce=secrets.token_bytes(8);image=bytearray(2048);completed=[];timings=[]
                order=range(128) if number==1 else range(127,-1,-1)
                for block in order:
                    value=parse(exchange(request(block,nonce),number),block,nonce)
                    if value['status']!='ok':raise RuntimeError(f'Storage read failed: {value}')
                    image[value['offset']:value['offset']+16]=bytes.fromhex(value['data_hex'])
                    completed.append(block);timings.append(value['elapsed_ms'])
                    if len(completed)%32==0:print(f'[PASS {number}/2] {len(completed)}/128 blocks',flush=True)
                path=out/f'storage-pass{number}.bin'
                with path.open('xb') as f:f.write(image)
                manifest['passes'].append(dict(file=path.name,bytes=len(image),order='ascending' if number==1 else 'descending',
                    nonce=nonce.hex(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    block_elapsed_ms_range=[min(timings),max(timings)]))
            first=(out/'storage-pass1.bin').read_bytes();second=(out/'storage-pass2.bin').read_bytes()
            if first!=second:raise ValueError('Two external-storage reads differ')
            manifest['settings_checks']=settings_checks(first)
            nonce=secrets.token_bytes(8)
            after=monitor.parse(exchange(monitor.request(0,nonce)),0,nonce);manifest['gui_after']=after
            if after['state']!='GUI' or after['error']:raise RuntimeError('GUI error after reads')
            manifest['complete']=True;manifest['two_passes_equal']=True;status=0
        except Exception as exc:manifest['error']=f'{type(exc).__name__}: {exc}'
        finally:
            if device is not None:device.close()
            with (out/'manifest.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
    # Keep full storage bytes/packet trace private; summarize hashes and checks.
    print(json.dumps(manifest,indent=2));print('Private evidence:',out)
    return status

if __name__=='__main__':raise SystemExit(main())
