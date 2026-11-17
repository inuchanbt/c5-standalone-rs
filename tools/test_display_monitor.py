import struct,unittest
import display_monitor as display
class DisplayWireTests(unittest.TestCase):
    def reply(self,age=10,valid=1,ma=-100,mv=5000):
        b=bytearray(64);b[:2]=b'\xff\x55';b[8:10]=bytes([0xa9,52]);b[10:26]=b'C5V1'+struct.pack('<I',1)+b'12345678'
        struct.pack_into('<5Ii3I',b,26,1,0,1,valid,mv,ma,2,age,0)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255;return bytes(b)
    def test_signed_current_preserved(self):
        r=display.parse(self.reply(),1,b'12345678');self.assertEqual(r['current_mA'],-100);self.assertTrue(r['reading_valid'])
    def test_stale_overrange_corrupt_replies_rejected(self):
        bad=bytearray(self.reply());bad[40]^=1
        for b in [self.reply(age=501),self.reply(ma=-1101),self.reply(mv=5501),bytes(bad)]:
            with self.assertRaises(ValueError):display.parse(b,1,b'12345678')
        with self.assertRaises(ValueError):display.parse(self.reply(),2,b'12345678')
        self.assertFalse(display.parse(self.reply(age=600,valid=0),1,b'12345678')['reading_valid'])
if __name__=='__main__':unittest.main()
