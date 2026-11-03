import os
import sys
import unittest

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compressor import get_algorithm
from compressor.lz77 import compress_bytes, decompress_bytes


class TestLZ77(unittest.TestCase):
    def test_roundtrip_small_string(self):
        data = b"HELLO HELLO HELLO"
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_repeating_patterns(self):
        data = b"ABABABABABABABABAB"
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_binary_data(self):
        data = bytes(range(64)) * 4
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_empty_input(self):
        data = b""
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_small_inputs(self):
        for data in [b"A", b"AB"]:
            encoded = compress_bytes(data)
            decoded = decompress_bytes(encoded)
            self.assertEqual(decoded, data)

    def test_levels(self):
        data = b"ABABABABABABABABABABAB"
        for level in range(1, 6):
            encoded = compress_bytes(data, level=level)
            decoded = decompress_bytes(encoded)
            self.assertEqual(decoded, data)

    def test_large_text(self):
        data = (b"the quick brown fox jumps over the lazy dog " * 200)
        encoded = compress_bytes(data, level=5)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_interface_roundtrip(self):
        algo = get_algorithm("lz77")
        data = b"XYZXYZXYZXYZ"
        self.assertEqual(algo.decompress(algo.compress(data)), data)


if __name__ == "__main__":
    unittest.main()
