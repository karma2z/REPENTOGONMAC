import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).parents[1] / 'compatibility/preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def pe():
    data = bytearray(1024)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, 0x84, 0x14c, 1, 0, 0, 0, 224, 2)
    struct.pack_into('<H', data, 0x98, 0x10b)
    struct.pack_into('<I', data, 0xa8, 0x1000)
    struct.pack_into('<I', data, 0xb4, 0x400000)
    struct.pack_into('<8sIIIIIIHHI', data, 0x178, b'.text', 512, 0x1000, 512, 512, 0, 0, 0, 0, 0x60000020)
    return data


class PreflightTests(unittest.TestCase):
    def test_identity_is_never_approval(self):
        result = preflight.report(pe())
        self.assertFalse(result['matches_requested_identity'])
        self.assertFalse(result['safe_to_install'])
        self.assertEqual(result['runtime_compatibility'], 'UNVERIFIED')

    def test_matching_identity_is_still_not_approval(self):
        data = pe()
        original = preflight.TARGET
        try:
            preflight.TARGET = dict(size=len(data), sha256=preflight.hashlib.sha256(data).hexdigest())
            result = preflight.report(data)
            self.assertTrue(result['matches_requested_identity'])
            self.assertFalse(result['safe_to_install'])
        finally:
            preflight.TARGET = original

    def test_rejects_truncated_headers(self):
        data = pe()
        for length in (0, 2, 63, 128, 150, 380, 400):
            with self.subTest(length=length), self.assertRaises(ValueError):
                preflight.inspect_pe(data[:length])

    def test_rejects_section_outside_file(self):
        data = pe()
        struct.pack_into('<I', data, 0x178 + 20, 1000)
        with self.assertRaises(ValueError):
            preflight.inspect_pe(data)

    def test_rejects_wrong_architecture(self):
        data = pe()
        struct.pack_into('<H', data, 0x84, 0x8664)
        with self.assertRaises(ValueError):
            preflight.inspect_pe(data)

    def test_rejects_dll(self):
        data = pe()
        struct.pack_into('<H', data, 0x96, 0x2002)
        with self.assertRaises(ValueError):
            preflight.inspect_pe(data)

    def test_rejects_entry_outside_code(self):
        data = pe()
        struct.pack_into('<I', data, 0xa8, 0x5000)
        with self.assertRaises(ValueError):
            preflight.inspect_pe(data)

    def test_version_string_is_not_identity(self):
        data = pe()
        data[600:615] = b'1.9.7.17.J460\0\0\0'
        result = preflight.report(data)
        self.assertIn('1.9.7.17.J460', result['version_strings'])
        self.assertFalse(result['matches_requested_identity'])


if __name__ == '__main__':
    unittest.main()
