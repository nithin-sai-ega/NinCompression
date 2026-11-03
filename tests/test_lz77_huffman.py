import os
import sys
import unittest

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compressor import get_algorithm
from compressor.lz77_huffman import LZ77Huffman


class TestLZ77Huffman(unittest.TestCase):
    def test_roundtrip_text(self):
        data = b"the quick brown fox jumps over the lazy dog " * 10
        algo = LZ77Huffman()
        encoded = algo.compress(data)
        decoded = algo.decompress(encoded)
        self.assertEqual(decoded, data)

    def test_roundtrip_binary(self):
        data = bytes(range(128)) * 3
        algo = LZ77Huffman()
        encoded = algo.compress(data)
        decoded = algo.decompress(encoded)
        self.assertEqual(decoded, data)

    def test_empty_input(self):
        data = b""
        algo = LZ77Huffman()
        encoded = algo.compress(data)
        decoded = algo.decompress(encoded)
        self.assertEqual(decoded, data)

    def test_registry(self):
        algo = get_algorithm("lz77h")
        data = b"ABABABABABABAB"
        self.assertEqual(algo.decompress(algo.compress(data)), data)


if __name__ == "__main__":
    unittest.main()
