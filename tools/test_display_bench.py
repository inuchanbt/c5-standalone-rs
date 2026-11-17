import unittest
from unittest.mock import patch
from bench_compare import DisplayC5,GatedC5

class DisplayBenchTests(unittest.TestCase):
    def status(self,number=4,valid=True):
        return dict(settings_state='READY',settings_error=0,conversion_error=False,
                    reading_valid=valid,sample_number=number,autonomous_enabled=valid)
    def raw(self,n):return dict(gated_cache=dict(sample_number=n),raw=dict(gui_measurement_updates=False))
    def test_associates_display_and_raw_by_sequence(self):
        d=DisplayC5.__new__(DisplayC5);d.display_status=lambda:self.status()
        with patch.object(GatedC5,'sample',side_effect=[self.raw(3),self.raw(4)]):r=d.sample()
        self.assertEqual(r['display']['sample_number'],4);self.assertTrue(r['raw']['gui_measurement_updates'])
    def test_missing_gui_value_aborts(self):
        d=DisplayC5.__new__(DisplayC5);d.display_status=lambda:self.status(valid=False)
        with patch.object(GatedC5,'sample',return_value=self.raw(4)),self.assertRaises(RuntimeError):d.sample()
    def test_unmatched_sequences_do_not_return_false_association(self):
        d=DisplayC5.__new__(DisplayC5);d.display_status=lambda:self.status()
        with patch.object(GatedC5,'sample',side_effect=[self.raw(1),self.raw(2),self.raw(3)]),self.assertRaises(RuntimeError):d.sample()
    def test_stop_requires_missing_gui_and_autonomous_disabled(self):
        d=DisplayC5.__new__(DisplayC5)
        with patch.object(GatedC5,'stop_shadow',return_value=dict(state='OFF')),patch('bench_compare.time.sleep'):
            d.display_status=lambda:self.status()
            with self.assertRaises(RuntimeError):d.stop_shadow()
            d.display_status=lambda:self.status(valid=False)
            self.assertFalse(d.stop_shadow()['display']['reading_valid'])
if __name__=='__main__':unittest.main()
