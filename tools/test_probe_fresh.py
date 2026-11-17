"""Freshness probe parsing preserves raw flags without claiming qualified samples."""
import struct
import unittest
import probe_fresh


class FreshWireTests(unittest.TestCase):
    nonce=b'12345678'
    def reply(self,status=0,count=8,mfg=0x5449,flags=None,stage=0):
        flags=flags or [3,1,3,1,3,1,3,1]
        b=bytearray(64);b[:2]=b'\xff\x55';b[8:10]=bytes([0x9f,52]);b[10:26]=b'C5F1'+struct.pack('<I',1)+self.nonce
        struct.pack_into('<4B4H8H2I',b,26,status,2,3,count,0,0xfb68,mfg,0x2281,*flags,37,stage)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255;return bytes(b)
    def test_preserves_set_clear_memory_flags_and_marks_side_effects(self):
        r=probe_fresh.parse(self.reply(flags=[2,0,3,1,3,1,3,1]),1,self.nonce)
        self.assertEqual(r['conversion_ready'][:2],[True,False]);self.assertEqual(r['memory_ok'][:2],[False,False])
        self.assertFalse(r['freshness_qualified']);self.assertTrue(r['read_to_clear_side_effects_possible'])
        r=probe_fresh.parse(self.reply(status=2,count=2,stage=0xb01),1,self.nonce)
        self.assertEqual(r['diag_hex'],['0x3','0x1']);self.assertEqual(r['status'],'nack')
    def test_rejects_stale_corrupt_and_false_success(self):
        wrong=bytearray(self.reply());wrong[30]^=1
        for data,seq in [(bytes(wrong),1),(self.reply(),2),(self.reply(count=7),1),(self.reply(mfg=0),1)]:
            with self.assertRaises(ValueError):probe_fresh.parse(data,seq,self.nonce)


if __name__=='__main__':unittest.main()
