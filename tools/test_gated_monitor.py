"""Gate-cache wire checks distinguish acquisition counters from ADC evidence."""
import struct
import unittest
import gated_monitor as gated


class GatedWireTests(unittest.TestCase):
    nonce=b'12345678'
    def reply(self,command=0xa2,state=2,phase=6,error=0,flags=15,number=3,age=10,gate=20,step=2):
        b=bytearray(64);b[:2]=b'\xff\x55';b[8:10]=bytes([command+1,52])
        b[10:26]=b'C5N1'+struct.pack('<I',5)+self.nonce
        if command==0xa6:struct.pack_into('<9I',b,26,number,960,970,20,4,3,30,50,3)
        else:struct.pack_into('<4B5I6H',b,26,state,phase,error,flags,number,1000,age,0xfda2c0,0x065030,0,0xfb68,step,20,gate,50)
        b[62]=sum(b[8:62])&255;b[63]=sum(b[:62])&255
        return bytes(b)
    def test_preserves_signed_raw_and_associates_gate_without_qualifying_gui_or_analog_accuracy(self):
        status=gated.parse(0xa2,self.reply(),5,self.nonce)
        evidence=gated.parse(0xa6,self.reply(command=0xa6),5,self.nonce)
        self.assertTrue(status['completion_gate_observed']);self.assertTrue(status['cache_current'])
        self.assertTrue(gated.validate_evidence(status,evidence));self.assertEqual(status['shunt_raw'],'0xfda2c0')
        self.assertFalse(status['freshness_qualified']);self.assertFalse(status['gui_measurement_updates'])
    def test_rejects_corruption_stale_nonce_and_wrong_command(self):
        b=bytearray(self.reply());b[40]^=1
        for data,seq,nonce,command in [(bytes(b),5,self.nonce,0xa2),(self.reply(),6,self.nonce,0xa2),
                (self.reply(),5,b'87654321',0xa2),(self.reply(),5,self.nonce,0xa0)]:
            with self.assertRaises(ValueError):gated.parse(command,data,seq,nonce)
    def test_rejects_false_gate_current_age_and_timing_claims(self):
        for data in [self.reply(flags=11),self.reply(number=0),self.reply(age=501),
                     self.reply(phase=10),self.reply(gate=1001),self.reply(step=13),self.reply(state=0)]:
            with self.assertRaises(ValueError):gated.parse(0xa2,data,5,self.nonce)
        old=gated.parse(0xa2,self.reply(state=0,flags=13,age=1000),5,self.nonce)
        self.assertFalse(old['cache_current']);self.assertTrue(old['cache_available'])
        failed=gated.parse(0xa2,self.reply(state=3,flags=13,error=9,step=13),5,self.nonce)
        self.assertEqual(failed['error'],9);self.assertFalse(failed['cache_current'])
        stopped=gated.parse(0xa4,self.reply(command=0xa4,state=0,flags=13,error=9,step=13),5,self.nonce)
        self.assertEqual(stopped['state'],'OFF');self.assertEqual(stopped['error'],9)
    def test_sequence_mismatch_keeps_unassociated_evidence_and_deadlines_reject_false_gate(self):
        status=gated.parse(0xa2,self.reply(),5,self.nonce)
        evidence=gated.parse(0xa6,self.reply(command=0xa6,number=4),5,self.nonce)
        self.assertFalse(gated.validate_evidence(status,evidence))
        evidence['sample_number']=3;evidence['sample_ready_observed_tick']=400
        with self.assertRaises(ValueError):gated.validate_evidence(status,evidence)
        evidence.update(sample_clear_observed_tick=960,sample_ready_observed_tick=970,ready_event_count=2)
        with self.assertRaises(ValueError):gated.validate_evidence(status,evidence)
    def test_gate_deadline_comparison_handles_tick_wrap(self):
        status=dict(sample_number=1,acquisition_completed_tick=20)
        evidence=dict(sample_number=1,sample_clear_observed_tick=0xfffffff0,sample_ready_observed_tick=5,
            ready_event_count=1,clear_event_count=1)
        self.assertTrue(gated.validate_evidence(status,evidence))


if __name__=='__main__':unittest.main()
