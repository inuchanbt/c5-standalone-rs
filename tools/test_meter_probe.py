"""Run the actual native I2C ID probe against injected line samples and faults."""
import ctypes
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from build import DEFAULT_LLVM, ROOT
import probe_meter
import storage_backup

class Result(ctypes.Structure):
    _fields_=[('status',ctypes.c_uint8),('kind',ctypes.c_uint8),('lines',ctypes.c_uint8),
              ('valid',ctypes.c_uint8),('m3e',ctypes.c_uint16),('d3f',ctypes.c_uint16),
              ('mfe',ctypes.c_uint16),('dff',ctypes.c_uint16),('elapsed',ctypes.c_uint32),
              ('stage',ctypes.c_uint16),('reads',ctypes.c_uint16)]

class RawResult(ctypes.Structure):
    _fields_=[('status',ctypes.c_uint8),('kind',ctypes.c_uint8),('lines',ctypes.c_uint8),
              ('reserved',ctypes.c_uint8),('valid',ctypes.c_uint16),('config',ctypes.c_uint16),
              ('adc',ctypes.c_uint16),('cal',ctypes.c_uint16),('tempco',ctypes.c_uint16),
              ('temp',ctypes.c_uint16),('shunt',ctypes.c_uint32),('bus',ctypes.c_uint32),
              ('elapsed',ctypes.c_uint32),('stage',ctypes.c_uint32),('reads',ctypes.c_uint32)]

class StorageResult(ctypes.Structure):
    _fields_=[('status',ctypes.c_uint8),('count',ctypes.c_uint8),('lines',ctypes.c_uint8),
              ('reserved',ctypes.c_uint8),('offset',ctypes.c_uint16),('stage',ctypes.c_uint16),
              ('elapsed',ctypes.c_uint32),('data',ctypes.c_uint8*16)]

class FreshResult(ctypes.Structure):
    _fields_=[('status',ctypes.c_uint8),('kind',ctypes.c_uint8),('lines',ctypes.c_uint8),
              ('count',ctypes.c_uint8),('config',ctypes.c_uint16),('adc',ctypes.c_uint16),
              ('manufacturer',ctypes.c_uint16),('device',ctypes.c_uint16),
              ('diag',ctypes.c_uint16*8),('elapsed',ctypes.c_uint32),('stage',ctypes.c_uint32)]

HARNESS=r'''
#include "meter_probe.h"
#include "meter_fresh.h"
int dll_entry(void *module,unsigned reason,void *reserved){return 1;}
struct fake {
    const uint8_t *samples;unsigned size,index,levels,steps,budget,clock_fault,clock_reads;
    uint8_t *trace;unsigned trace_size;
};
static void set(void *p,unsigned line,unsigned released){
    struct fake *f=p;
    if(released)f->levels|=1u<<line;else f->levels&=~(1u<<line);
    if(f->trace_size<4096)f->trace[f->trace_size++]=(uint8_t)((line<<1)|released);
}
static unsigned get(void *p,unsigned line){
    struct fake *f=p;
    if(line==C5_SCL){f->clock_reads++;return f->clock_fault&&f->clock_reads>=f->clock_fault?0:f->levels&1;}
    return f->index<f->size?f->samples[f->index++]:1;
}
static int pause(void *p){struct fake *f=p;return ++f->steps<=f->budget;}
__declspec(dllexport) unsigned simulate(const uint8_t *samples,unsigned size,unsigned budget,
    unsigned clock_fault,struct c5_meter_result *out,uint8_t *trace,unsigned *count){
    struct fake f={samples,size,0,3,0,budget,clock_fault,0,trace,0};
    const struct c5_meter_io io={&f,set,get,pause};c5_meter_probe(&io,out);
    *count=f.trace_size;return (f.levels<<16)|f.index;
}
__declspec(dllexport) unsigned simulate_raw(const uint8_t *samples,unsigned size,unsigned budget,
    unsigned clock_fault,struct c5_meter_raw_result *out,uint8_t *trace,unsigned *count){
    struct fake f={samples,size,0,3,0,budget,clock_fault,0,trace,0};
    const struct c5_meter_io io={&f,set,get,pause};c5_meter_raw_probe(&io,out);
    *count=f.trace_size;return (f.levels<<16)|f.index;
}
__declspec(dllexport) unsigned simulate_storage(const uint8_t *samples,unsigned size,unsigned block,
    unsigned fault,struct c5_storage_result *out,uint8_t *trace,unsigned *count){
    struct fake f={samples,size,0,3,0,5000,fault,0,trace,0};
    const struct c5_meter_io io={&f,set,get,pause};c5_storage_read_block(&io,block,out);
    *count=f.trace_size;return (f.levels<<16)|f.index;
}
__declspec(dllexport) unsigned simulate_fresh(const uint8_t *samples,unsigned size,unsigned budget,
    unsigned fault,struct c5_fresh_result *out,uint8_t *trace,unsigned *count){
    struct fake f={samples,size,0,3,0,budget,fault,0,trace,0};
    const struct c5_meter_io io={&f,set,get,pause};c5_meter_fresh_probe(&io,out);
    *count=f.trace_size;return (f.levels<<16)|f.index;
}
'''

@unittest.skipUnless((DEFAULT_LLVM/'clang.exe').is_file(),'LLVM clang is required')
class NativeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
        cls.directory=tempfile.TemporaryDirectory(prefix='meter-probe-test-',dir=cache)
        source=Path(cls.directory.name)/'probe.c';library=source.with_suffix('.dll')
        source.write_text(HARNESS,encoding='ascii')
        p=subprocess.run([str(DEFAULT_LLVM/'clang.exe'),'--target=x86_64-w64-windows-gnu',
            '-shared','-nostdlib','-Wl,--entry,dll_entry','-O2','-Wall','-Werror',
            '-I',str(ROOT/'native'),str(source),'-o',str(library)],capture_output=True,timeout=30)
        if p.returncode:cls.directory.cleanup();raise RuntimeError(p.stderr.decode(errors='replace'))
        cls.dll=ctypes.CDLL(str(library));cls.simulate=cls.dll.simulate
        cls.simulate.argtypes=[ctypes.POINTER(ctypes.c_uint8),ctypes.c_uint,ctypes.c_uint,
            ctypes.c_uint,ctypes.POINTER(Result),ctypes.POINTER(ctypes.c_uint8),ctypes.POINTER(ctypes.c_uint)]
        cls.simulate.restype=ctypes.c_uint
        cls.simulate_raw=cls.dll.simulate_raw
        cls.simulate_raw.argtypes=list(cls.simulate.argtypes)
        cls.simulate_raw.argtypes=cls.simulate_raw.argtypes[:4]+[ctypes.POINTER(RawResult)]+cls.simulate_raw.argtypes[5:]
        cls.simulate_raw.restype=ctypes.c_uint
        cls.simulate_storage=cls.dll.simulate_storage
        cls.simulate_storage.argtypes=cls.simulate.argtypes[:4]+[ctypes.POINTER(StorageResult)]+cls.simulate.argtypes[5:]
        cls.simulate_storage.restype=ctypes.c_uint
        cls.simulate_fresh=cls.dll.simulate_fresh
        cls.simulate_fresh.argtypes=cls.simulate.argtypes[:4]+[ctypes.POINTER(FreshResult)]+cls.simulate.argtypes[5:]
        cls.simulate_fresh.restype=ctypes.c_uint
    @classmethod
    def tearDownClass(cls):
        free=ctypes.WinDLL('kernel32',use_last_error=True).FreeLibrary
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_int
        if not free(cls.dll._handle):raise ctypes.WinError(ctypes.get_last_error())
        cls.directory.cleanup()
    def run_probe(self,samples,budget=5000,clock_fault=0,raw=False):
        data=(ctypes.c_uint8*len(samples))(*samples);result=RawResult() if raw else Result()
        trace=(ctypes.c_uint8*4096)();count=ctypes.c_uint()
        simulate=self.simulate_raw if raw else self.simulate
        end=simulate(data,len(samples),budget,clock_fault,ctypes.byref(result),trace,ctypes.byref(count))
        self.assertEqual(end>>16,3,'Both lines must be released even after a fault')
        return result,bytes(trace[:count.value]),end&65535
    def samples(self,*words):
        return [1]+[bit for word in words for bit in [0,0,0]+[(word>>i)&1 for i in range(15,-1,-1)]]
    def segments(self,trace):
        levels=3;segments=[];current=None
        for event in trace:
            line=event>>1;released=event&1;before=levels
            levels=(levels|(1<<line)) if released else (levels&~(1<<line))
            if line==1 and before&1:
                if before&2 and not levels&2:current=[];segments.append(current)
                elif not before&2 and levels&2:current=None
            if line==0 and not before&1 and levels&1 and current is not None:
                current.append((levels>>1)&1)
        return segments
    def check_reads_only(self,trace,registers,counts=None,addresses=None):
        groups=self.segments(trace);self.assertEqual(len(groups),2*len(registers))
        counts=counts or [2]*len(registers)
        addresses=addresses or [0x40]*len(registers)
        byte=lambda bits:sum(bit<<(7-i) for i,bit in enumerate(bits))
        for index,reg in enumerate(registers):
            write,read=groups[index*2:index*2+2]
            self.assertEqual(len(write),19) # address + pointer + ACKs + repeated START setup
            self.assertEqual(len(read),10+9*counts[index])
            address=addresses[index]
            self.assertEqual([byte(write[:8]),byte(write[9:17]),byte(read[:8])],[address<<1,reg,(address<<1)|1])
            for i in range(counts[index]):
                self.assertEqual(read[17+9*i],int(i==counts[index]-1))
    def test_identifies_ina228_and_only_reads_two_ids(self):
        samples=self.samples(0x5449,0x2281);r,trace,used=self.run_probe(samples)
        self.assertEqual((r.status,r.kind,r.valid,r.reads),(0,2,3,2))
        self.assertEqual((r.m3e,r.d3f),(0x5449,0x2281));self.assertEqual(used,len(samples))
        self.check_reads_only(trace,[0x3e,0x3f])
    def test_identifies_ina226_with_independent_id_pair(self):
        samples=self.samples(0,0,0x5449,0x2260);r,trace,used=self.run_probe(samples)
        self.assertEqual((r.status,r.kind,r.valid,r.reads),(0,1,15,4))
        self.assertEqual(used,len(samples));self.check_reads_only(trace,[0x3e,0x3f,0xfe,0xff])
    def test_unknown_or_wrong_manufacturer_does_not_label_sensor(self):
        r,trace,_=self.run_probe(self.samples(0x5448,0x2281,0x5448,0x2260))
        self.assertEqual((r.status,r.kind,r.valid),(1,0,15))
        self.check_reads_only(trace,[0x3e,0x3f,0xfe,0xff])
    def test_nack_stops_at_exact_failed_phase_without_retry(self):
        for phase in (1,2,3):
            with self.subTest(phase=phase):
                r,_,used=self.run_probe([1]+[0]*(phase-1)+[1])
                self.assertEqual((r.status,r.reads,r.valid,r.stage),(2,0,0,0x3e00|phase))
                self.assertEqual(used,phase+1)
    def test_busy_clock_timeout_and_total_deadline_release_lines(self):
        for samples,budget,clock_fault,status in [([0],5000,0,3),([1],5000,1,3),
                ([1],5000,2,4),([1],1,0,4)]:
            with self.subTest(status=status,budget=budget,clock_fault=clock_fault):
                r,trace,_=self.run_probe(samples,budget,clock_fault)
                self.assertEqual((r.status,r.kind,r.reads),(status,0,0))
                self.assertLess(len(trace),40)

    def test_raw_snapshot_reads_only_allowed_registers_after_identity(self):
        values=[(0x5449,2),(0x2281,2),(0x10,2),(0xfb68,2),(0x1000,2),
                (0,2),(0xffffff,3),(0x061a80,3),(0x0cc0,2)]
        samples=[1]+[bit for value,count in values for bit in
                     [0,0,0]+[(value>>i)&1 for i in range(count*8-1,-1,-1)]]
        # The raw probe identifies the device first, then reuses that bus.
        r,trace,used=self.run_probe(samples,raw=True)
        self.assertEqual((r.status,r.kind,r.valid,r.reads),(0,2,127,9))
        self.assertEqual((r.config,r.adc,r.cal,r.tempco,r.shunt,r.bus,r.temp),
                         (0x10,0xfb68,0x1000,0,0xffffff,0x061a80,0x0cc0))
        self.assertEqual(used,len(samples))
        self.check_reads_only(trace,[0x3e,0x3f,0,1,2,3,4,5,6],[count for _,count in values])

    def fresh_probe(self,samples,budget=5000):
        data=(ctypes.c_uint8*len(samples))(*samples);r=FreshResult()
        trace=(ctypes.c_uint8*4096)();count=ctypes.c_uint()
        result=self.simulate_fresh(data,len(samples),budget,0,ctypes.byref(r),trace,ctypes.byref(count))
        self.assertEqual(result>>16,3)
        return r,bytes(trace[:count.value]),result&65535

    def test_fresh_probe_reads_only_eight_diag_words_after_identity_and_config(self):
        flags=[3,1,3,1,3,1,3,1]
        samples=self.samples(0x5449,0x2281,0,0xfb68,*flags)
        r,trace,used=self.fresh_probe(samples)
        self.assertEqual((r.status,r.kind,r.count,r.stage),(0,2,8,0))
        self.assertEqual(list(r.diag),flags);self.assertEqual(used,len(samples))
        self.check_reads_only(trace,[0x3e,0x3f,0,1]+[0x0b]*8)

    def test_fresh_probe_rejects_unknown_configuration_before_any_diag_read(self):
        r,trace,_=self.fresh_probe(self.samples(0x5449,0x2281,0,0))
        self.assertEqual((r.status,r.count),(6,0));self.check_reads_only(trace,[0x3e,0x3f,0,1])
        r,trace,_=self.fresh_probe(self.samples(0,0,0x5449,0x2260))
        self.assertEqual((r.status,r.kind,r.count),(6,1,0));self.check_reads_only(trace,[0x3e,0x3f,0xfe,0xff])

    def test_fresh_probe_preserves_partial_flags_and_stops_without_retry(self):
        r,_,_=self.fresh_probe(self.samples(0x5449,0x2281,0,0xfb68,3,1)+[1])
        self.assertEqual((r.status,r.count,r.stage),(2,2,0x0b01));self.assertEqual(list(r.diag)[:2],[3,1])
        r,trace,_=self.fresh_probe([1],budget=1)
        self.assertEqual((r.status,r.count),(4,0));self.assertLess(len(trace),40)

    def test_raw_snapshot_rejects_other_models_and_preserves_partial_failure(self):
        r,trace,_=self.run_probe(self.samples(0,0,0x5449,0x2260),raw=True)
        self.assertEqual((r.status,r.kind,r.valid,r.reads),(6,1,0,4))
        self.check_reads_only(trace,[0x3e,0x3f,0xfe,0xff])
        samples=self.samples(0x5449,0x2281,0x10)+[1] # NACK ADC config address
        r,_,used=self.run_probe(samples,raw=True)
        self.assertEqual((r.status,r.kind,r.valid,r.reads,r.stage),(2,2,1,3,0x0101))
        self.assertEqual(r.config,0x10);self.assertEqual(used,len(samples))

    def storage_probe(self,block,samples,fault=0):
        array=(ctypes.c_uint8*len(samples))(*samples);result=StorageResult()
        trace=(ctypes.c_uint8*4096)();count=ctypes.c_uint()
        end=self.simulate_storage(array,len(samples),block,fault,ctypes.byref(result),trace,ctypes.byref(count))
        self.assertEqual(end>>16,3)
        return result,bytes(trace[:count.value]),end&65535

    def test_storage_all_128_blocks_use_only_stock_read_addresses(self):
        for block in range(128):
            payload=bytes((block*7+i*11)&255 for i in range(16))
            samples=[1,0,0,0]+[(value>>i)&1 for value in payload for i in range(7,-1,-1)]
            r,trace,used=self.storage_probe(block,samples)
            self.assertEqual((r.status,r.count,r.offset),(0,16,block*16))
            self.assertEqual(bytes(r.data),payload);self.assertEqual(used,len(samples))
            self.check_reads_only(trace,[block*16&255],[16],[0x50+(block>>4)])

    def test_storage_rejects_out_of_range_without_io_and_stops_on_nack(self):
        for block in (128,0xffffffff):
            r,trace,used=self.storage_probe(block,[])
            self.assertEqual((r.status,r.count,len(trace),used),(7,0,0,0))
        r,trace,used=self.storage_probe(127,[1,0,1])
        self.assertEqual((r.status,r.count,r.offset,r.stage),(2,0,0x7f0,0xf002))
        self.assertEqual(used,3);self.assertLess(len(trace),120)

class ProbeWireTests(unittest.TestCase):
    def fixture(self):
        seq=77;nonce=b'12345678';b=bytearray(probe_meter.request(seq,nonce))
        b[8:10]=bytes([0x93,36]);struct.pack_into('<4B4HI2H',b,26,0,2,3,3,0x5449,0x2281,0,0,5,0,2)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        return b,seq,nonce
    def test_parses_verified_id_pair_without_manufacturing_measurements(self):
        b,seq,nonce=self.fixture();v=probe_meter.parse(bytes(b),seq,nonce)
        self.assertEqual(v['model'],'INA228');self.assertEqual(v['id_registers']['0x3e'],'0x5449')
        self.assertIsNone(v['id_registers']['0xfe']);self.assertNotIn('voltage',v)
        self.assertEqual(probe_meter.parse(b'\0'+b,seq,nonce),v)
    def test_rejects_corrupt_stale_and_false_model_claims(self):
        b,seq,nonce=self.fixture()
        for at in (0,8,9,10,26,30,62,63):
            altered=bytearray(b);altered[at]^=1
            with self.assertRaises(ValueError):probe_meter.parse(altered,seq,nonce)
        with self.assertRaises(ValueError):probe_meter.parse(b,seq+1,nonce)
        with self.assertRaises(ValueError):probe_meter.parse(b,seq,b'87654321')
        b[30]^=1;b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        with self.assertRaises(ValueError):probe_meter.parse(b,seq,nonce)

    def test_raw_wire_preserves_codes_and_rejects_incomplete_success(self):
        seq=7;nonce=b'raw-test';b=bytearray(probe_meter.raw_request(seq,nonce))
        b[8:10]=bytes([0x95,52]);struct.pack_into('<4B6H5I',b,26,0,2,3,0,
            127,0x10,0xfb68,0x1000,0,0x0cc0,0xffffff,0x061a80,28,0,9)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        result=probe_meter.parse_raw(b,seq,nonce)
        self.assertEqual(result['raw_registers']['0x04'],'0xffffff')
        self.assertFalse(result['calibrated']);self.assertFalse(result['freshness_qualified'])
        self.assertNotIn('current',result)
        with self.assertRaises(ValueError):probe_meter.parse_raw(b,seq+1,nonce)
        b[30]=63;b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        with self.assertRaises(ValueError):probe_meter.parse_raw(b,seq,nonce)

    def test_storage_wire_and_pass_nonce_reject_stale_or_incomplete_data(self):
        block=127;nonce=b'pass-two';b=bytearray(storage_backup.request(block,nonce))
        b[8:10]=bytes([0x97,44]);struct.pack_into('<4BHHI16s',b,26,0,16,3,0,block*16,0,15,bytes(range(16)))
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        self.assertEqual(storage_backup.parse(b,block,nonce)['data_hex'],bytes(range(16)).hex())
        with self.assertRaises(ValueError):storage_backup.parse(b,block,b'pass-one')
        with self.assertRaises(ValueError):storage_backup.parse(b,block-1,nonce)
        with self.assertRaises(ValueError):storage_backup.request(128,nonce)
        b[27]=15;b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        with self.assertRaises(ValueError):storage_backup.parse(b,block,nonce)

    def test_stock_settings_checks_detect_each_block_corruption(self):
        image=bytearray(2048)
        ranges=[(0,0x1b),(0x1c,0x6f),(0x70,0x9f),(0xa0,0xe9)]
        for _,end in ranges:image[end]=0xa5
        self.assertTrue(all(c['matches'] for c in storage_backup.settings_checks(image)))
        for index,(start,_) in enumerate(ranges):
            altered=bytearray(image);altered[start]^=1
            checks=storage_backup.settings_checks(altered)
            self.assertEqual([c['matches'] for c in checks],[i!=index for i in range(4)])

    def test_storage_not_ready_is_reported_even_without_a_valid_offset(self):
        block=24;nonce=b'notready';b=bytearray(storage_backup.request(block,nonce))
        b[8:10]=bytes([0x97,44]);struct.pack_into('<4BHHI16s',b,26,5,0,0,0,0,0,0,b'\0'*16)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        self.assertEqual(storage_backup.parse(b,block,nonce)['status'],'gui_not_ready')

if __name__=='__main__':unittest.main()
