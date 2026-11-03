import unittest

from helpers import sample_inputs

from compressor import get_algorithm
from main import compress_file, decompress_file


class TestStore(unittest.TestCase):
    def test_store_roundtrip(self):
        algo = get_algorithm("store")
        for name, data in sample_inputs().items():
            with self.subTest(name):
                self.assertEqual(algo.decompress(algo.compress(data)), data)


class TestAuto(unittest.TestCase):
    def test_auto_roundtrips_everything(self):
        for name, data in sample_inputs().items():
            with self.subTest(name):
                packed, _ = compress_file(data, algorithm="auto")
                restored, _ = decompress_file(packed)
                self.assertEqual(restored, data)

    def test_auto_is_never_larger_than_any_single_algorithm(self):
        data = sample_inputs()["text"]
        auto_size = len(compress_file(data, algorithm="auto")[0])
        for name in ("rle", "huffman", "lz77", "lz77h", "store"):
            with self.subTest(name):
                # A few bytes of slack: the algorithm name in the header differs in length.
                self.assertLessEqual(auto_size, len(compress_file(data, algorithm=name)[0]) + 8)

    def test_auto_falls_back_to_store_for_random_data(self):
        data = sample_inputs()["random"]
        packed, _ = compress_file(data, algorithm="auto")
        # Header: magic(4) + alg_len(1) + name + size(8) + crc(4); payload is the raw data.
        self.assertEqual(packed[5 : 5 + packed[4]], b"store")
        self.assertEqual(len(packed), len(data) + 4 + 1 + len(b"store") + 8 + 4)

    def test_auto_picks_a_real_algorithm_for_compressible_data(self):
        data = sample_inputs()["text"]
        packed, _ = compress_file(data, algorithm="auto")
        self.assertNotEqual(packed[5 : 5 + packed[4]], b"store")
        self.assertLess(len(packed), len(data))

    def test_unknown_algorithm_is_rejected(self):
        with self.assertRaises(KeyError):
            compress_file(b"abc", algorithm="nope")


if __name__ == "__main__":
    unittest.main()
