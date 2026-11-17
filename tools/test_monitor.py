import struct
import unittest
import monitor

class MonitorTests(unittest.TestCase):
    def fixture(self):
        nonce=bytes(range(8));seq=123;b=bytearray(monitor.request(seq,nonce))
        b[8:10]=bytes([0x91,52]);struct.pack_into('<BBH8I',b,26,2,5,0,1000,10,37,192000000,6000,60<<8,11,3)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        return bytes(b),seq,nonce
    def test_parses_real_wire_layout(self):
        raw,seq,nonce=self.fixture();v=monitor.parse(raw,seq,nonce)
        self.assertEqual(v['state'],'GUI');self.assertEqual(v['keys'],5)
        self.assertEqual(v['core_clock_hz'],192000000);self.assertEqual(v['lcd_ms'],37)
        self.assertEqual(v['blocked_actions'],3);self.assertEqual(v['brightness_percent'],60)
        self.assertEqual(monitor.parse(b'\0'+raw,seq,nonce),v)
    def test_rejects_stale_and_corrupt_replies(self):
        raw,seq,nonce=self.fixture()
        for data,s,n in [(raw,seq+1,nonce),(raw,seq,b'x'*8),(raw[:-1],seq,nonce)]:
            with self.assertRaises(ValueError):monitor.parse(data,s,n)
        for at in [0,8,9,10,26,40,62,63]:
            b=bytearray(raw);b[at]^=1
            with self.assertRaises(ValueError):monitor.parse(b,seq,nonce)

if __name__=='__main__':unittest.main()
