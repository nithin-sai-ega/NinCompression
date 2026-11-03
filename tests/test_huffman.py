import os
import sys
import unittest

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compressor import get_algorithm
from compressor.huffman import compress_bytes, decompress_bytes, compress_string, decompress_string


class TestHuffman(unittest.TestCase):
    def test_roundtrip_bytes(self):
        data = b"AAAABBBCCDAA" + bytes([0, 1, 2, 255, 255, 255])
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)

    def test_roundtrip_string(self):
        text = "the quick brown fox jumps over the lazy dog"
        encoded_hex = compress_string(text)
        decoded_text = decompress_string(encoded_hex)
        self.assertEqual(decoded_text, text)

    def test_interface_roundtrip(self):
        algo = get_algorithm("huffman")
        data = b"\x00\x00\x00\xff\xff\x01\x02\x02"
        self.assertEqual(algo.decompress(algo.compress(data)), data)

    def test_single_symbol(self):
        data = b"AAAAAA"
        encoded = compress_bytes(data)
        decoded = decompress_bytes(encoded)
        self.assertEqual(decoded, data)


if __name__ == "__main__":
    unittest.main()
