"""Execute the production flag-gated scheduler, including stuck/faulted ADCs."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest
from build import ROOT, DEFAULT_LLVM

HARNESS=r'''
#include "meter_gated.h"
#include <stddef.h>
void *memset(void *p,int value,size_t count){volatile unsigned char *q=p;while(count--)*q++=(unsigned char)value;return p;}
int dll_entry(void *module,unsigned reason,void *reserved){return 1;}
struct fake { unsigned calls,scenario,diag,config,presenting,inside,data;uint8_t registers[256]; };
static unsigned read_register(void *p,unsigned reg,unsigned count,uint32_t *value,uint32_t *elapsed){
    struct fake *f=p;unsigned n=f->calls++;
    if(n<256)f->registers[n]=(uint8_t)reg;
    if(f->presenting)f->inside++;
    *elapsed=f->scenario==7?13:2;
    if(count!=((reg==4||reg==5)?3u:2u))return 99;
    *value=reg==0x3e?0x5449:reg==0x3f?0x2281:reg==1?0xfb68:reg==4?0xfed1c0:reg==5?0x064560:0;
    if(reg==0){f->config++;if((f->scenario==6&&f->config==2)||f->scenario==13)*value=0x10;}
    if(reg==0x0b){
        const unsigned pattern[]={3,3,1,1,3};*value=pattern[f->diag++%5];
        if(f->scenario==1||(f->scenario==10&&f->diag>5))*value=3;
        if(f->scenario==2)*value=1;
        if(f->scenario==3)*value=2;
        if(f->scenario==4)*value=0x8003;
    }
    if(reg==4||reg==5)f->data++;
    if(f->scenario==5&&reg==5)return 2;
    if(f->scenario==14&&reg==4)*value|=1;
    return 0;
}
__declspec(dllexport) unsigned scenario(unsigned which){
    struct c5_gated_sampler g={0};struct c5_sampler *s=&g.s;struct fake f={0};f.scenario=which;
    uint32_t base=which==8?0xfffffff0u:0;
    c5_gated_step(&g,base,0,read_register,&f);if(f.calls)return 1;
    c5_gated_start(&g,base);c5_gated_step(&g,base,1,read_register,&f);if(f.calls)return 2;
    unsigned delayed=0;
    for(unsigned tick=0;tick<1800;tick++){
        if(which==11&&s->phase==6&&!delayed){tick+=153;delayed=1;}
        if(which==12&&s->phase==7&&!delayed){tick+=76;delayed=1;}
        uint32_t now=base+tick;s->heartbeat=now;
        f.presenting=which==9&&tick%100<37;
        c5_gated_step(&g,now,f.presenting,read_register,&f);
    }
    unsigned expected=which==1||which==2||which==10||which==11?11:
        which==3||which==4?12:which==5?2:which==6||which==14?8:which==7||which==12?9:which==13?7:0;
    if(expected){
        if(s->state!=C5_SAMPLE_FAULT||s->error!=expected)return 100+s->error;
        if(s->sequence!=(which==10?1u:0u))return 3;
        if((which==1||which==2||which==3||which==4||which==11)&&f.data)return 4;
        if(c5_sampler_current(s,s->sample_tick))return 5;
        unsigned calls=f.calls;c5_gated_step(&g,base+1900,0,read_register,&f);
        if(f.calls!=calls)return 6;
    }else{
        if(s->state!=C5_SAMPLE_RUNNING||s->sequence<3||s->shunt!=0xfed1c0||s->bus!=0x064560)return 7;
        if(s->config||s->adc!=0xfb68||f.inside||s->max_transaction_ms!=2||s->pair_ms>75||s->cycle_ms>1200)return 8;
        const uint8_t expected_regs[]={0x3e,0x3f,0,1,0xb,0xb,0xb,0xb,0xb,4,5,0,1};
        for(unsigned i=0;i<sizeof(expected_regs);i++)if(f.registers[i]!=expected_regs[i])return 9;
        if((uint32_t)(s->sample_tick-g.sample_ready_tick)>150||
           (uint32_t)(g.sample_ready_tick-g.sample_clear_tick)>500||!g.clear_events||!g.ready_events)return 10;
        if(!c5_sampler_current(s,s->sample_tick+500)||c5_sampler_current(s,s->sample_tick+501))return 11;
        unsigned calls=f.calls;c5_gated_step(&g,s->heartbeat+2001,0,read_register,&f);
        if(s->state!=C5_SAMPLE_OFF||f.calls!=calls)return 12;
    }
    c5_gated_start(&g,2000);
    if(s->sequence||s->phase||s->error||s->state!=C5_SAMPLE_IDENTIFY||g.diag_reads||g.sample_ready_tick)return 13;
    return 0;
}
'''


@unittest.skipUnless((DEFAULT_LLVM/'clang.exe').is_file(),'LLVM required')
class GatedSamplerTests(unittest.TestCase):
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
    def test_requires_clear_then_set_before_any_data_read_and_publishes_bounded_cache(self):self.check(0)
    def test_stuck_ready_cannot_reuse_completion_and_stops(self):self.check(1)
    def test_missing_completion_stops_without_partial_publication(self):self.check(2)
    def test_bad_memory_status_stops(self):self.check(3)
    def test_unsupported_latched_status_stops(self):self.check(4)
    def test_transport_failure_is_sticky_without_partial_publication(self):self.check(5)
    def test_configuration_change_prevents_publication(self):self.check(6)
    def test_register_deadline_stops(self):self.check(7)
    def test_tick_wrap_preserves_gate_deadlines_and_cache_age(self):self.check(8)
    def test_lcd_scanout_never_performs_register_read(self):self.check(9)
    def test_later_gate_failure_invalidates_old_cache(self):self.check(10)
    def test_post_ready_delay_cannot_publish_stale_sample(self):self.check(11)
    def test_pair_span_limit_stops(self):self.check(12)
    def test_unsupported_initial_configuration_stops(self):self.check(13)
    def test_reserved_data_bits_reject_sample(self):self.check(14)


if __name__=='__main__':unittest.main()
