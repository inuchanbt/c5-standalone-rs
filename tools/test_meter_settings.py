"""Execute the production flag-gated scheduler, including stuck/faulted ADCs."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest
from build import ROOT, DEFAULT_LLVM

HARNESS=r'''
#include "meter_settings.h"
#include <stddef.h>
void *memset(void *p,int value,size_t n){volatile unsigned char *q=p;while(n--)*q++=(unsigned char)value;return p;}
int dll_entry(void *p,unsigned r,void *s){return 1;}
static unsigned mode,calls,accepts;
static unsigned read_block(void *p,unsigned block,uint8_t *data){
 (void)p;if(block!=calls%15)return 99;
 for(unsigned i=0;i<16;i++)data[i]=(uint8_t)(block*16+i);
 calls++;if(mode==1&&calls==18)data[7]^=1;
 if(mode==2&&calls==3)return 2;return 0;
}
static unsigned accept(const uint8_t *data){
 accepts++;for(unsigned i=0;i<240;i++)if(data[i]!=(uint8_t)i)return 0;
 return mode!=3;
}
__declspec(dllexport) unsigned scenario(unsigned n){
 struct c5_settings_load s={0};mode=n;calls=0;accepts=0;
 for(unsigned i=0;i<40;i++)c5_settings_step(&s,read_block,0,accept);
 if(n==0)return !(s.state==1&&calls==30&&accepts==1);
 if(n==1)return !(s.state==2&&calls==18&&accepts==0&&s.error==20);
 if(n==2)return !(s.state==2&&calls==3&&accepts==0&&s.error==2);
 return !(s.state==2&&calls==30&&accepts==1&&s.error==21);
}
'''

@unittest.skipUnless((DEFAULT_LLVM/'clang.exe').is_file(),'LLVM required')
class SettingsLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory(prefix='gated-',dir=ROOT/'.cache')
        source=Path(cls.directory.name)/'gated.c';library=source.with_suffix('.dll')
        source.write_text(HARNESS,encoding='ascii')
        result=subprocess.run([str(DEFAULT_LLVM/'clang.exe'),'--target=x86_64-w64-windows-gnu',
            '-shared','-nostdlib','-Wl,--entry,dll_entry','-O2','-Wall','-Werror',
            '-I',str(ROOT/'native'),str(source),'-o',str(library)],capture_output=True,timeout=30)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
        cls.dll=ctypes.CDLL(str(library));cls.dll.scenario.argtypes=[ctypes.c_uint];cls.dll.scenario.restype=ctypes.c_uint
    @classmethod
    def tearDownClass(cls):
        free=ctypes.WinDLL('kernel32',use_last_error=True).FreeLibrary
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_int
        if not free(cls.dll._handle):raise ctypes.WinError(ctypes.get_last_error())
        cls.directory.cleanup()
    def check(self,n):self.assertEqual(self.dll.scenario(n),0)
    def test_both_complete_passes_required_before_accept(self):self.check(0)
    def test_second_pass_mismatch_stops_before_accept(self):self.check(1)
    def test_transport_error_stops_without_retry(self):self.check(2)
    def test_invalid_calibration_is_sticky(self):self.check(3)



if __name__=='__main__':unittest.main()
