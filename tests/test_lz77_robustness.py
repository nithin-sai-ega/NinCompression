import random
import unittest

from helpers import sample_inputs

from compressor.lz77 import compress_bytes, decompress_bytes


class TestLZ77Robustness(unittest.TestCase):
    def test_match_at_the_edge_of_the_window(self):
        # The same 20-byte block repeats exactly 4096 bytes later (the maximum offset).
        block = bytes(range(100, 120))
        filler = bytes((i * 7 + 3) % 251 for i in range(4096 - len(block)))
        data = block + filler + block
        self.assertEqual(decompress_bytes(compress_bytes(data, level=5)), data)

    def test_overlapping_match(self):
        data = b"a" * 500 + b"ab" * 200
        for level in range(1, 6):
            with self.subTest(level=level):
                self.assertEqual(decompress_bytes(compress_bytes(data, level=level)), data)

    def test_random_inputs_roundtrip(self):
        rng = random.Random(99)
        for _ in range(60):
            n = rng.randint(0, 1500)
            alphabet = rng.choice([2, 4, 16, 256])
            data = bytes(rng.randrange(alphabet) for _ in range(n))
            level = rng.randint(1, 5)
            with self.subTest(n=n, alphabet=alphabet, level=level):
                self.assertEqual(decompress_bytes(compress_bytes(data, level=level)), data)

    def test_every_sample_input_at_every_level(self):
        for name, data in sample_inputs().items():
            for level in range(1, 6):
                with self.subTest(name=name, level=level):
                    self.assertEqual(decompress_bytes(compress_bytes(data, level=level)), data)

    def test_highest_level_is_not_worse_than_lowest(self):
        data = (b"abcabcabd abcabcabe " * 100) + bytes(range(256)) * 4
        low = len(compress_bytes(data, level=1))
        high = len(compress_bytes(data, level=5))
        self.assertLessEqual(high, low)

    def test_repetitive_text_gets_smaller(self):
        data = sample_inputs()["text"]
        self.assertLess(len(compress_bytes(data)), len(data))

    def test_invalid_level_is_rejected(self):
        for bad in (0, 6, -1):
            with self.subTest(level=bad):
                with self.assertRaises(ValueError):
                    compress_bytes(b"abc", level=bad)

    def test_corrupt_stream_is_rejected(self):
        with self.assertRaises(ValueError):
            decompress_bytes(b"\x00\x00\x01")  # not a multiple of 4 bytes
        with self.assertRaises(ValueError):
            decompress_bytes(bytes([0, 5, 3, 65]))  # offset points before the start


if __name__ == "__main__":
    unittest.main()
