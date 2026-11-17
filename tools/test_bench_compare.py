"""Host-injected checks for the bench adapter; never connects to instruments."""
from types import SimpleNamespace
import unittest
from pathlib import Path
from bench_compare import paired_read, reference, asd_arguments, load_module, load_is_off, ensure_capture_health, ShadowC5, ASD


def reading(v=5, i=.1):
    return SimpleNamespace(voltage_v=v,current_a=i,power_w=v*i,raw_response=b'raw')


class BenchTests(unittest.TestCase):
    def test_idle_usb_reads_do_not_mask_missing_or_stalled_scope_stream(self):
        good=dict(updated=100,error=None,scope_samples=250,scope_progress_at=100)
        ensure_capture_health(good,True,101)
        for state in [dict(good,scope_samples=0),dict(good,updated=105,scope_progress_at=100),dict(good,error='USB timeout')]:
            with self.assertRaises(RuntimeError):ensure_capture_health(state,True,105)
        with self.assertRaises(RuntimeError):ensure_capture_health(good,False,101)
    @unittest.skipUnless(ASD.is_file(), 'Owner ASD CLI checkout required')
    def test_actual_cli_parser_accepts_bounded_arguments_without_opening_devices(self):
        cli=load_module('c5_asd_parser_test',ASD)
        argv=asd_arguments(SimpleNamespace(port='COM3',current=.1,seconds=10),Path('D:/c5_standalone_rs/build/parser-only'))
        parsed=cli.build_parser().parse_args(argv)
        self.assertEqual(parsed.hold,(5.0,.1,10.0,'fixed'))
        self.assertFalse(parsed.pdo_auto_reconcile)
        self.assertTrue(parsed.query_pdo_official)
        self.assertEqual(parsed.official_prime_current,0)
        self.assertEqual(parsed.current_policy,'skip')

    @unittest.skipUnless(ASD.is_file(), 'Owner ASD CLI checkout required')
    def test_actual_status_decoder_and_off_verification_use_public_dictionary(self):
        cli=load_module('c5_asd_status_test',ASD)
        from asd_pd31_modules.utils import append_crc
        payload=bytes.fromhex('00 00 00 00 00 00 00 00 01 14 00 00 00 09 00 09 00 00 0F A0 00 00 00')
        status=cli.decode_standard_power_load_status_diagnostic(append_crc(bytes.fromhex('01 12 0D 17')+payload))
        self.assertTrue(load_is_off(status))
        active=bytearray(payload);active[10]=1
        status=cli.decode_standard_power_load_status_diagnostic(append_crc(bytes.fromhex('01 12 0D 17')+active))
        self.assertFalse(load_is_off(status))

    def test_brackets_c5_with_two_real_references_in_order(self):
        events=[]
        def measure(): events.append('asd'); return reading()
        def sample(): events.append('c5'); return {'raw':'actual'}
        first,pair=paired_read(measure,sample,lambda:events.append('off'),lambda:events.append('health'))
        self.assertEqual(events,['health','asd','c5','asd','health'])
        self.assertEqual(pair['c5'],{'raw':'actual'})
        self.assertFalse(pair['exactly_synchronous'])
        self.assertEqual(pair['asd_after']['current_A'],.1)
        self.assertLessEqual(pair['start']['monotonic_ns'],pair['c5_start']['monotonic_ns'])
        self.assertLessEqual(pair['c5_end']['monotonic_ns'],pair['end']['monotonic_ns'])

    def test_c5_or_capture_failure_stops_load_and_does_not_complete_pair(self):
        for where in ('c5','health'):
            with self.subTest(where=where):
                stops=[];reads=[]
                def fail(): raise RuntimeError('injected')
                def measure(): reads.append(1); return reading()
                with self.assertRaisesRegex(RuntimeError,'injected'):
                    paired_read(measure,fail if where=='c5' else lambda:None,
                                lambda:stops.append(1),fail if where=='health' else lambda:None)
                self.assertEqual(stops,[1])
                self.assertEqual(len(reads),1 if where=='c5' else 0)

    def test_rejects_missing_nonfinite_or_outside_envelope_readings(self):
        for v,i in [(6,.1),(5,1.2),(float('nan'),.1),(5,float('inf'))]:
            with self.subTest(v=v,i=i),self.assertRaises(ValueError): reference(reading(v,i))

    def test_bad_second_reference_stops_load_and_preserves_failure(self):
        values=iter([reading(),reading(7)]);stops=[]
        with self.assertRaises(ValueError):
            paired_read(lambda:next(values),lambda:{'raw':'ok'},lambda:stops.append(1),lambda:None)
        self.assertEqual(stops,[1])

    def cache(self,state='RUNNING',number=1,error=0):
        return dict(state=state,sample_number=number,error=error,cache_current=state=='RUNNING',
            config='0x0',adc_config='0xfb68',shunt_raw='0xfed1c0',bus_raw='0x064560')

    def shadow(self,states):
        c5=ShadowC5.__new__(ShadowC5);c5.shadow_started=False;c5.sampler_generation=0
        c5.commands=[];iterator=iter(states)
        def exchange(command):c5.commands.append(command);return next(iterator)
        c5.shadow_exchange=exchange;c5.gui=lambda:dict(error=0)
        return c5

    def test_shadow_uses_new_counter_instead_of_initial_cached_value(self):
        c5=self.shadow([self.cache(number=7),self.cache(number=7),self.cache(number=8)])
        result=c5.sample()
        self.assertEqual(result['shadow_cache']['sample_number'],8)
        self.assertEqual(result['read_source'],'shadow-cache')
        self.assertFalse(result['raw']['freshness_qualified'])
        self.assertNotIn(0x94,c5.commands)

    def test_shadow_restarts_after_lease_off_and_stops_explicitly(self):
        c5=self.shadow([self.cache('OFF',9),self.cache('IDENTIFY',0),self.cache(number=1),self.cache('OFF',1)])
        result=c5.sample();self.assertEqual(result['sampler_generation'],1)
        self.assertEqual(c5.stop_shadow()['state'],'OFF')
        self.assertEqual(c5.commands,[0x9a,0x98,0x9a,0x9c])

    def test_shadow_fault_never_restarts_or_returns_cached_data(self):
        c5=self.shadow([self.cache('FAULT',5,error=2)])
        with self.assertRaisesRegex(RuntimeError,'no automatic restart'):c5.sample()
        self.assertEqual(c5.commands,[0x9a])


if __name__=='__main__':unittest.main()
