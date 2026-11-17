"""Shadow wire format rejects stale, corrupt and falsely current cache claims."""
import struct
import unittest
import shadow_monitor as shadow


class ShadowWireTests(unittest.TestCase):
    nonce=b'12345678'
    def reply(self,command=0x9a,flags=7,age=10,number=3,state=2):
        b=bytearray(64);b[:2]=b'\xff\x55';b[8:10]=bytes([command+1,52])
        b[10:26]=b'C5S1'+struct.pack('<I',5)+self.nonce
        struct.pack_into('<4B5I6H',b,26,state,4,0,flags,number,1000,age,0xfda2c0,0x065030,0,0xfb68,4,50,20,100)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255;return bytes(b)
    def test_preserves_packed_negative_raw_and_does_not_claim_adc_freshness(self):
        r=shadow.parse(0x9a,self.reply(),5,self.nonce)
        self.assertTrue(r['cache_current']);self.assertEqual(r['shunt_raw'],'0xfda2c0')
        self.assertFalse(r['freshness_qualified']);self.assertFalse(r['gui_measurement_updates'])
    def test_rejects_bad_checksum_nonce_and_reply_command(self):
        b=bytearray(self.reply());b[40]^=1
        for raw,seq,nonce,command in [(bytes(b),5,self.nonce,0x9a),(self.reply(),6,self.nonce,0x9a),
                (self.reply(),5,b'87654321',0x9a),(self.reply(),5,self.nonce,0x98)]:
            with self.assertRaises(ValueError):shadow.parse(command,raw,seq,nonce)
    def test_rejects_false_current_cache_and_accepts_stopped_old_cache(self):
        for b in [self.reply(age=501),self.reply(number=0),self.reply(state=0)]:
            with self.assertRaises(ValueError):shadow.parse(0x9a,b,5,self.nonce)
        r=shadow.parse(0x9a,self.reply(flags=5,age=1000,state=0),5,self.nonce)
        self.assertFalse(r['cache_current']);self.assertTrue(r['cache_available'])


if __name__=='__main__':unittest.main()
