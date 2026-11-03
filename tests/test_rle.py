import os
import sys
import unittest

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compressor import get_algorithm
from compressor.rle import compress_bytes, decompress_bytes, compress_string, decompress_string


class TestRLE(unittest.TestCase):
    def test_roundtrip_bytes(self):
        data = b"AAAABBBCCDAA" + bytes([0, 0, 0, 255, 255])
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_roundtrip_string(self):
        text = "AAABBBCCDAA"
        encoded_hex = compress_string(text)
        decoded_text = decompress_string(encoded_hex)
        self.assertEqual(decoded_text, text)

    def test_interface_roundtrip(self):
        algo = get_algorithm("rle")
        data = b"ZZZZYYYXX"
        self.assertEqual(algo.decompress(algo.compress(data)), data)

    def test_invalid_length(self):
        with self.assertRaises(ValueError):
            decompress_bytes(b"\x03")


if __name__ == "__main__":
    unittest.main()
