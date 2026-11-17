import unittest
from stack_audit import estimate

class StackAuditTests(unittest.TestCase):
    def test_detects_original_oversized_startup(self):
        text='0800b1dc <init>:\n 800b1dc: b5f0\tpush\t{r4, r5, r6, r7, lr}\n 800b1e0: e92d 0700\tpush.w\t{r8, r9, r10}\n 800b1e4: f5ad 5d67\tsub.w\tsp, sp, #0x39c0\n 800b1e8: b086\tsub\tsp, #0x18\n'
        self.assertEqual(estimate(text)['init'],14840)
        self.assertGreater(estimate(text)['init'],8192)
    def test_counts_in_place_startup_and_rejects_dynamic_adjustment(self):
        text='0800b1dc <init>:\n 800b1dc: b5f0\tpush\t{r4, r5, r6, r7, lr}\n 800b1e0: f84d 8d04\tstr\tr8, [sp, #-4]!\n 800b1e4: b0ec\tsub\tsp, #0x1b0\n'
        self.assertEqual(estimate(text)['init'],456)
        with self.assertRaises(ValueError):estimate(text+' 800b1e6: f5ad 5d67\tsub.w\tsp, sp, r0\n')

if __name__=='__main__':unittest.main()
