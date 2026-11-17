"""Execute production shadow-sampler timing, fault and publication logic on host."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest
from build import ROOT, DEFAULT_LLVM

HARNESS=r'''
#include "meter_sampler.h"
int dll_entry(void *module,unsigned reason,void *reserved){return 1;}
struct fake { unsigned calls,scenario,presenting,inside;uint8_t registers[64]; };
static unsigned read_register(void *p,unsigned reg,unsigned count,uint32_t *value,uint32_t *elapsed){
    struct fake *f=p;unsigned n=f->calls++;
    if(n<64)f->registers[n]=(uint8_t)reg;
    if(f->presenting)f->inside++;
    *elapsed=3;
    if(count!=((reg==4||reg==5)?3u:2u))return 99;
    *value=reg==0x3e?0x5449:reg==0x3f?0x2281:reg==1?0xfb68:reg==4?0xfed1c0:reg==5?0x064560:0;
    if(f->scenario==1&&n==5)return 2;
    if(f->scenario==2&&reg==1)*value=0;
    if(f->scenario==3&&reg==0&&n>8)*value=0x10;
    if(f->scenario==4)*elapsed=13;
    return 0;
}
__declspec(dllexport) unsigned scenario(unsigned which){
    struct c5_sampler s={0};struct fake f={0};f.scenario=which;
    if(which==0){
        c5_sampler_step(&s,1,0,read_register,&f);if(f.calls)return 1;
        c5_sampler_start(&s,0);c5_sampler_step(&s,0,1,read_register,&f);if(f.calls)return 2;
    }else c5_sampler_start(&s,0);
    uint32_t base=which==5?0xfffffff0u:0;
    if(which==5)c5_sampler_start(&s,base); /* active start renews lease, reset due below */
    if(which==5){s=(struct c5_sampler){0};c5_sampler_start(&s,base);}
    for(unsigned tick=0;tick<1400;tick++){
        uint32_t now=base+tick;s.heartbeat=now;
        f.presenting=which==6&&tick%100<37;
        c5_sampler_step(&s,now,f.presenting,read_register,&f);
    }
    if(which==1||which==2||which==4){
        if(s.state!=C5_SAMPLE_FAULT||s.sequence)return 3;
        unsigned expected=which==1?2:which==2?7:9;if(s.error!=expected)return 4;
        unsigned calls=f.calls;c5_sampler_step(&s,1500,0,read_register,&f);
        if(f.calls!=calls)return 5;return 0;
    }
    if(which==3){
        if(s.state!=C5_SAMPLE_FAULT||s.error!=8||s.sequence!=1)return 6;
        if(c5_sampler_current(&s,1400))return 7;return 0;
    }
    if(s.state!=C5_SAMPLE_RUNNING||s.sequence<3||s.shunt!=0xfed1c0||s.bus!=0x064560)return 8;
    if(s.config||s.adc!=0xfb68||f.inside||s.max_transaction_ms!=3||s.max_pair_ms>75||s.cycle_ms>160)return 9;
    static const uint8_t expected[]={0x3e,0x3f,0,1,4,5,0,1};
    for(unsigned i=0;i<8;i++)if(f.registers[i]!=expected[i])return 10;
    if(!c5_sampler_current(&s,s.sample_tick+500)||c5_sampler_current(&s,s.sample_tick+501))return 11;
    unsigned calls=f.calls;c5_sampler_step(&s,s.heartbeat+2001,0,read_register,&f);
    if(s.state!=C5_SAMPLE_OFF||f.calls!=calls)return 12;
    c5_sampler_start(&s,2000);if(s.sequence||s.phase||s.error||s.state!=C5_SAMPLE_IDENTIFY)return 13;
    return 0;
}
'''


@unittest.skipUnless((DEFAULT_LLVM/'clang.exe').is_file(),'LLVM required')
class SamplerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory(prefix='sampler-',dir=ROOT/'.cache')
        source=Path(cls.directory.name)/'sampler.c';library=source.with_suffix('.dll')
        source.write_text(HARNESS,encoding='ascii')
        subprocess.run([str(DEFAULT_LLVM/'clang.exe'),'--target=x86_64-w64-windows-gnu',
            '-shared','-nostdlib','-Wl,--entry,dll_entry','-O2','-Wall','-Werror',
            '-I',str(ROOT/'native'),str(source),'-o',str(library)],check=True,capture_output=True,timeout=30)
        cls.dll=ctypes.CDLL(str(library));cls.dll.scenario.argtypes=[ctypes.c_uint];cls.dll.scenario.restype=ctypes.c_uint
    @classmethod
    def tearDownClass(cls):
        free=ctypes.WinDLL('kernel32',use_last_error=True).FreeLibrary
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_int
        if not free(cls.dll._handle):raise ctypes.WinError(ctypes.get_last_error())
        cls.directory.cleanup()
    def check(self,n):self.assertEqual(self.dll.scenario(n),0)
    def test_fixed_read_order_publish_stale_cache_lease_and_restart(self):self.check(0)
    def test_nack_fault_is_sticky_without_retry_or_partial_publication(self):self.check(1)
    def test_shutdown_or_other_adc_configuration_is_rejected(self):self.check(2)
    def test_changed_configuration_stops_and_invalidates_cached_sample(self):self.check(3)
    def test_transaction_deadline_does_not_publish(self):self.check(4)
    def test_tick_wrap_preserves_deadlines_and_cache_age(self):self.check(5)
    def test_lcd_busy_intervals_never_execute_register_read(self):self.check(6)


if __name__=='__main__':unittest.main()
