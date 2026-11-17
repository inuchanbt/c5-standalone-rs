import struct
import unittest
from package import encode, decode, audit

def fixture():
    raw=bytearray(b'\xff'*0x2000)
    struct.pack_into('<II',raw,0,0x20017000,0x08005001)
    struct.pack_into('<I',raw,36*4,0x080029ed)
    raw[0x810:0x814]=b'C400'
    return raw

class PackageTests(unittest.TestCase):
    def test_roundtrip_and_corruption(self):
        raw=fixture(); package=encode(raw)
        self.assertEqual(decode(package)[:len(raw)],raw)
        for at in [0,20,40,0x2000,len(package)-1]:
            b=bytearray(package); b[at]^=1
            with self.assertRaises(ValueError):decode(b)

    def test_preservation_audit_rejects_region_corruption(self):
        package=encode(fixture()); payload=bytearray(decode(package));payload[0xc00]=0xfe
        baseline=bytes((i*17+3)%256 for i in range(0x100000))
        actual=bytearray(baseline);actual[0x4000:0xe3fd0]=payload;actual[0xe3fd0:0xe4000]=b'\xff'*48
        self.assertTrue(audit(actual,package,baseline)['passed'])
        for at in [0,0x3800,0x4000,0x4c00,0xe3fd0,0xe4000,0xff800]:
            b=bytearray(actual);b[at]^=1
            self.assertFalse(audit(b,package,baseline)['passed'])

    def test_rejects_unqualified_vectors_and_tags(self):
        for at in [0,4,36*4,0x810,0xc00]:
            raw=fixture();raw[at]^=1
            with self.assertRaises(ValueError):encode(raw)

if __name__=='__main__':unittest.main()
