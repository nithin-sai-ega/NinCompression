"""Decompressors must reject bad input with ValueError, never crash another way."""

import random
import unittest

from helpers import sample_inputs

from compressor import get_algorithm


class TestCorruptInput(unittest.TestCase):
    def assert_clean(self, name, payload):
        """Decompressing must either succeed or raise ValueError."""
        try:
            get_algorithm(name).decompress(payload)
        except ValueError:
            pass

    def test_random_garbage(self):
        rng = random.Random(2024)
        for name in ("rle", "huffman", "lz77", "lz77h", "store"):
            for _ in range(150):
                garbage = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 60)))
                with self.subTest(name=name, garbage=garbage.hex()):
                    self.assert_clean(name, garbage)

    def test_every_truncation_of_a_valid_stream(self):
        data = sample_inputs()["text"][:300]
        for name in ("rle", "huffman", "lz77", "lz77h"):
            packed = get_algorithm(name).compress(data)
            for cut in range(0, len(packed), max(1, len(packed) // 40)):
                with self.subTest(name=name, cut=cut):
                    self.assert_clean(name, packed[:cut])

    def test_bit_flips_in_a_valid_stream(self):
        rng = random.Random(7)
        data = sample_inputs()["text"][:300]
        for name in ("rle", "huffman", "lz77", "lz77h"):
            packed = get_algorithm(name).compress(data)
            for _ in range(80):
                damaged = bytearray(packed)
                damaged[rng.randrange(len(damaged))] ^= 1 << rng.randrange(8)
                with self.subTest(name=name):
                    self.assert_clean(name, bytes(damaged))

    def test_huffman_tree_that_never_ends(self):
        # Header claims 4000 tree bits, all zeros: "internal node" forever.
        payload = (4000).to_bytes(4, "big") + (0).to_bytes(4, "big") + bytes(500)
        with self.assertRaises(ValueError):
            get_algorithm("huffman").decompress(payload)


if __name__ == "__main__":
    unittest.main()
