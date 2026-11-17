"""The loaded bench must not accept an old or unassociated gated sample."""
import unittest
from unittest.mock import patch
from bench_compare import GatedC5

def cache(n=1,state='RUNNING',error=0):
    return dict(state=state,error=error,sample_number=n,cache_current=state=='RUNNING',
        completion_gate_observed=True,acquisition_completed_tick=100,
        config='0x0',adc_config='0xfb68',shunt_raw='0xfffff0',bus_raw='0x64000')

def evidence(n=1):
    return dict(sample_number=n,sample_clear_observed_tick=50,sample_ready_observed_tick=60,
                clear_event_count=n,ready_event_count=n)

class GatedBenchTests(unittest.TestCase):
    def device(self,replies):
        dev=GatedC5.__new__(GatedC5);dev.shadow_started=False;dev.sampler_generation=0
        dev.commands=[];it=iter(replies)
        def exchange(command):dev.commands.append(command);return next(it)
        dev.gated_exchange=exchange;dev.gui=lambda:dict(error=0)
        return dev
    def test_new_cache_and_same_sequence_evidence_required(self):
        dev=self.device([cache(7),cache(7),cache(8),evidence(9),cache(9),evidence(9)])
        with patch('bench_compare.time.sleep'):result=dev.sample()
        self.assertEqual(result['gated_cache']['sample_number'],9)
        self.assertEqual(result['gate_evidence']['sample_number'],9)
        self.assertFalse(result['raw']['freshness_qualified'])
        self.assertEqual(dev.commands,[0xa2,0xa2,0xa2,0xa6,0xa2,0xa6])
    def test_lease_off_restarts_with_new_generation_and_explicit_stop(self):
        dev=self.device([cache(9,'OFF'),cache(0,'IDENTIFY'),cache(),evidence(),cache(1,'OFF')])
        self.assertEqual(dev.sample()['sampler_generation'],1)
        self.assertEqual(dev.stop_shadow()['state'],'OFF')
        self.assertEqual(dev.commands,[0xa2,0xa0,0xa2,0xa6,0xa4])
    def test_fault_never_restarts(self):
        dev=self.device([cache(1,'FAULT',11)])
        with self.assertRaisesRegex(RuntimeError,'no automatic restart'):dev.sample()
        self.assertEqual(dev.commands,[0xa2])
    def test_invalid_evidence_aborts_instead_of_returning_raw_data(self):
        bad=evidence();bad['sample_ready_observed_tick']=1000
        dev=self.device([cache(0),cache(),bad])
        with self.assertRaises(ValueError):dev.sample()

if __name__=='__main__':unittest.main()
