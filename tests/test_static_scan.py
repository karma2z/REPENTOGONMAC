import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'compatibility'))
import static_scan


class StaticScanTests(unittest.TestCase):
    def test_overlapping_matches(self):
        self.assertEqual(static_scan.matches(b'\xaa\xaa\xaa', 'aaaa'), ([0, 1], False))

    def test_whole_byte_wildcards_match_runtime_semantics(self):
        self.assertEqual(static_scan.matches(b'\x55\xff\xec', '55?0ec'), ([0], False))

    def test_markers_do_not_change_raw_search(self):
        self.assertEqual(static_scan.matches(b'\x55\x11\xec', '.!55(??)ec'), ([0], False))

    def test_bounds_and_missing(self):
        self.assertEqual(static_scan.matches(b'\xaa', 'aabb'), ([], False))
        self.assertEqual(static_scan.matches(b'\xaa\xbb', 'ffaabb'), ([], False))

    def test_cap_is_explicit(self):
        self.assertEqual(static_scan.matches(b'\xaa' * 3, 'aa', limit=2), ([0, 1], True))

    def test_state_only_and_malformed_patterns_require_manual_review(self):
        for value in ('', '.', '55f', '????', '55xx'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                static_scan.matches(b'\x55\xff', value)

    def test_comments_do_not_remove_string_contents(self):
        text = '/* "aa": comment */\nasm Target "55??ec"; // "bb"\n'
        result = static_scan.uncomment(text)
        self.assertIn('asm Target "55??ec";', result)
        self.assertNotIn('comment', result)
        self.assertEqual(text.count('\n'), result.count('\n'))

    def test_registered_asm_and_main_are_in_inventory(self):
        entries = list(static_scan.inventory(Path(__file__).parents[1]))
        self.assertTrue(any(e['kind']=='asm' and e['name']=='DisableExitPrompt' for e in entries))
        self.assertTrue(any('IsaacMain(' in e['name'] for e in entries))


if __name__ == '__main__':
    unittest.main()
