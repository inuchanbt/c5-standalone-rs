"""Regression for the LCD timeout caused by a stream of I2C diagnostic jobs."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest
from build import ROOT, DEFAULT_LLVM

SOURCE=r'''
#include "diagnostic_queue.h"
int dll_entry(void *module,unsigned reason,void *reserved){return 1;}
__declspec(dllexport) unsigned prefix_test(void){
    struct c5_diagnostic_queue q={0};uint8_t a[16],b[16],out[16];
    for(unsigned i=0;i<16;i++){a[i]=(uint8_t)i;b[i]=(uint8_t)(i+99);out[i]=0;}
    if(c5_diagnostic_defer(&q,0,0x96,a))return 1;
    if(!c5_diagnostic_defer(&q,1,0x96,a))return 2;
    if(!c5_diagnostic_defer(&q,1,0x94,b))return 3;
    if(c5_diagnostic_take(&q,1,out))return 4;
    if(c5_diagnostic_take(&q,0,out)!=0x96)return 5;
    for(unsigned i=0;i<16;i++)if(out[i]!=a[i])return 6;
    if(c5_diagnostic_take(&q,0,out))return 7;
    return 0;
}
__declspec(dllexport) unsigned frame_model(unsigned deferred){
    struct c5_diagnostic_queue q={0};uint8_t prefix[16],out[16];
    unsigned now=0,jobs=0;
    while(jobs<128){
        unsigned start=now,waiting=0;
        for(unsigned row=0;row<172;row++){
            now+=215; /* synthetic ~37 ms LCD, not a measured benchmark */
            if(jobs<128&&!waiting){
                for(unsigned i=0;i<16;i++)prefix[i]=(uint8_t)(jobs+i);
                if(deferred&&c5_diagnostic_defer(&q,1,0x96,prefix))waiting=1;
                else{now+=12000;jobs++;} /* observed 12 ms storage job */
            }
            if(c5_diagnostic_take(&q,1,out))return 3;
            if(now-start>250000)return 1; /* reproduce old wall-time failure */
        }
        unsigned command=c5_diagnostic_take(&q,0,out);
        if(command){
            if(command!=0x96)return 4;
            for(unsigned i=0;i<16;i++)if(out[i]!=(uint8_t)(jobs+i))return 5;
            now+=12000;jobs++;
        }
    }
    return 0;
}
'''

@unittest.skipUnless((DEFAULT_LLVM/'clang.exe').is_file(),'LLVM clang is required')
class DiagnosticQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
        cls.directory=tempfile.TemporaryDirectory(prefix='diag-queue-',dir=cache)
        source=Path(cls.directory.name)/'queue.c';library=source.with_suffix('.dll')
        source.write_text(SOURCE,encoding='ascii')
        p=subprocess.run([str(DEFAULT_LLVM/'clang.exe'),'--target=x86_64-w64-windows-gnu',
            '-shared','-nostdlib','-Wl,--entry,dll_entry','-O2','-Wall','-Werror','-I',
            str(ROOT/'native'),str(source),'-o',str(library)],capture_output=True,timeout=30)
        if p.returncode:cls.directory.cleanup();raise RuntimeError(p.stderr.decode(errors='replace'))
        cls.dll=ctypes.CDLL(str(library));cls.dll.prefix_test.restype=ctypes.c_uint
        cls.dll.frame_model.argtypes=[ctypes.c_uint];cls.dll.frame_model.restype=ctypes.c_uint
    @classmethod
    def tearDownClass(cls):
        free=ctypes.WinDLL('kernel32',use_last_error=True).FreeLibrary
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_int
        if not free(cls.dll._handle):raise ctypes.WinError(ctypes.get_last_error())
        cls.directory.cleanup()
    def test_pending_request_nonce_is_preserved_and_only_consumed_outside_lcd(self):
        self.assertEqual(self.dll.prefix_test(),0)
    def test_continuous_jobs_reproduce_old_timeout_and_deferred_model_completes(self):
        self.assertEqual(self.dll.frame_model(0),1)
        self.assertEqual(self.dll.frame_model(1),0)

if __name__=='__main__':unittest.main()
