"""Exercise the real dual-read collector with an injected HID device."""
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import storage_backup

class FakeStorageDevice:
    def __init__(self,mismatch=False,nack=False):
        image=bytearray((index*31+17)&255 for index in range(2048))
        for start,end in [(0,0x1b),(0x1c,0x6f),(0x70,0x9f),(0xa0,0xe9)]:
            checksum=0xa5
            for value in image[start:end]:checksum^=value
            image[end]=checksum
        self.image=bytes(image);self.pending=None;self.closed=False
        self.requests=[];self.storage_count=0;self.mismatch=mismatch;self.nack=nack
    def open_path(self,path):pass
    def set_nonblocking(self,value):pass
    def close(self):self.closed=True
    def write(self,raw):
        tx=raw[1:];self.requests.append(tx);b=bytearray(tx)
        if tx[8]==0x90:
            b[8:10]=bytes([0x91,52])
            struct.pack_into('<BBH8I',b,26,2,0,0,1000,10,37,192000000,9472,60<<8,10,0)
        elif tx[8]==0x92:
            b[8:10]=bytes([0x93,36])
            struct.pack_into('<4B4HI2H',b,26,0,2,3,3,0x5449,0x2281,0,0,6,0,2)
        elif tx[8]==0x96:
            block=struct.unpack_from('<I',tx,14)[0];offset=block*16;self.storage_count+=1
            data=self.image[offset:offset+16]
            if self.mismatch and self.storage_count==129:data=bytes([data[0]^1])+data[1:]
            b[8:10]=bytes([0x97,44])
            struct.pack_into('<4BHHI16s',b,26,2 if self.nack else 0,0 if self.nack else 16,
                             3,0,offset,1 if self.nack else 0,15,data)
        else:raise AssertionError(f'Unexpected host command: {tx[8]:#x}')
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255;self.pending=bytes(b)
        return 65
    def read(self,count,timeout=0):
        result=self.pending;self.pending=None;return list(result) if result else []

class CollectorTests(unittest.TestCase):
    def run_collector(self,directory,device):
        hid=types.SimpleNamespace(enumerate=lambda *args:[dict(path=b'fake',serial_number='20211222')],
                                  device=lambda:device)
        with patch.dict(sys.modules,{'hid':hid}),patch.object(sys,'argv',['storage_backup.py','--output-dir',str(directory)]),contextlib.redirect_stdout(io.StringIO()):
            return storage_backup.main()
    def test_two_full_passes_have_distinct_nonces_and_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'evidence';device=FakeStorageDevice()
            self.assertEqual(self.run_collector(out,device),0)
            self.assertEqual((out/'storage-pass1.bin').read_bytes(),device.image)
            self.assertEqual((out/'storage-pass2.bin').read_bytes(),device.image)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertTrue(manifest['complete']);self.assertTrue(all(c['matches'] for c in manifest['settings_checks']))
            packets=[tx for tx in device.requests if tx[8]==0x96]
            blocks=[struct.unpack_from('<I',tx,14)[0] for tx in packets]
            self.assertEqual(blocks,list(range(128))+list(range(127,-1,-1)))
            self.assertNotEqual(packets[0][18:26],packets[128][18:26]);self.assertTrue(device.closed)
            with self.assertRaises(FileExistsError):self.run_collector(out,FakeStorageDevice())
            self.assertEqual((out/'storage-pass1.bin').read_bytes(),device.image)
    def test_dual_read_mismatch_retains_both_copies_and_does_not_claim_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'evidence';device=FakeStorageDevice(mismatch=True)
            self.assertEqual(self.run_collector(out,device),2)
            manifest=json.loads((out/'manifest.json').read_text())
            self.assertFalse(manifest['complete']);self.assertIn('differ',manifest['error'])
            self.assertNotEqual((out/'storage-pass1.bin').read_bytes(),(out/'storage-pass2.bin').read_bytes())
            self.assertTrue(device.closed);self.assertEqual(device.storage_count,256)
    def test_nack_stops_after_one_request_without_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'evidence';device=FakeStorageDevice(nack=True)
            self.assertEqual(self.run_collector(out,device),2)
            self.assertEqual(device.storage_count,1);self.assertTrue(device.closed)
            manifest=json.loads((out/'manifest.json').read_text());self.assertFalse(manifest['complete'])
            self.assertFalse((out/'storage-pass1.bin').exists());self.assertTrue((out/'wire-trace.jsonl').is_file())

if __name__=='__main__':unittest.main()
