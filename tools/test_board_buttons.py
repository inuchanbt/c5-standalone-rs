"""Exercise the real native GPIO decoder, including simultaneous presses."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest
from build import DEFAULT_LLVM, ROOT


@unittest.skipUnless((DEFAULT_LLVM / 'clang.exe').is_file(), 'LLVM clang is required')
class BoardButtonTests(unittest.TestCase):
    def test_physical_order_and_all_key_combinations(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='button-test-', dir=cache) as directory:
            source = Path(directory) / 'buttons.c'
            library = Path(directory) / 'buttons.dll'
            source.write_text(
                '#include "buttons.h"\n'
                'int dll_entry(void *module, unsigned reason, void *reserved) { return 1; }\n'
                '__declspec(dllexport) unsigned decode(unsigned a, unsigned b) {\n'
                '    return c5_keys_from_gpio(a, b);\n}\n', encoding='ascii')
            compiled = subprocess.run([
                str(DEFAULT_LLVM / 'clang.exe'), '--target=x86_64-w64-windows-gnu',
                '-shared', '-nostdlib', '-Wl,--entry,dll_entry', '-O2', '-Wall', '-Werror',
                '-I', str(ROOT / 'native'), str(source), '-o', str(library),
            ], capture_output=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stderr.decode(errors='replace'))
            dll = ctypes.CDLL(str(library))
            decode = dll.decode
            decode.argtypes = [ctypes.c_uint, ctypes.c_uint]
            decode.restype = ctypes.c_uint
            try:
                # Expectations follow the owner's physical labels, independently
                # of the decoder's expression: Back, Left(-), OK, Right(+).
                physical = [('b', 14, 8), ('b', 15, 1), ('a', 13, 4), ('a', 14, 2)]
                for pressed in range(16):
                    a = b = 0xffff
                    expected = 0
                    for index, (port, pin, logical) in enumerate(physical):
                        if pressed & (1 << index):
                            if port == 'a': a &= ~(1 << pin)
                            else: b &= ~(1 << pin)
                            expected |= logical
                    with self.subTest(physical_mask=pressed):
                        self.assertEqual(decode(a, b), expected)
                        # Unrelated GPIO inputs must not become key events.
                        self.assertEqual(decode(a & 0x6000, b & 0xc000), expected)
            finally:
                # Release the Windows loader's handle before deleting the DLL.
                free = ctypes.WinDLL('kernel32', use_last_error=True).FreeLibrary
                free.argtypes = [ctypes.c_void_p]
                free.restype = ctypes.c_int
                if not free(dll._handle): raise ctypes.WinError(ctypes.get_last_error())


if __name__ == '__main__': unittest.main()
