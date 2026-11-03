import unittest

from helpers import sample_inputs

from compressor import get_algorithm
from main import compress_file, decompress_file, get_file_info
from utils.file_format import (
    MAGIC_V1,
    MAGIC_V2,
    build_compressed_bytes,
    crc32_of,
    parse_container,
)


class TestIntegrity(unittest.TestCase):
    def test_new_files_use_version_2_with_checksum(self):
        data = b"hello hello hello hello"
        packed, _ = compress_file(data, algorithm="lz77")
        self.assertTrue(packed.startswith(MAGIC_V2))
        container = parse_container(packed)
        self.assertEqual(container.version, 2)
        self.assertEqual(container.crc32, crc32_of(data))
        self.assertEqual(container.original_size, len(data))

    def test_corruption_is_detected_for_every_algorithm(self):
        data = sample_inputs()["text"]
        for name in ("rle", "huffman", "lz77", "lz77h", "store"):
            with self.subTest(name):
                packed = bytearray(compress_file(data, algorithm=name)[0])
                header_len = parse_container(bytes(packed)).header_size
                # Flip one bit in the payload, a few bytes in so the stream stays parseable.
                packed[header_len + min(10, len(packed) - header_len - 1)] ^= 0x01
                with self.assertRaises(ValueError):
                    decompress_file(bytes(packed))

    def test_version_1_files_still_decompress(self):
        data = b"AAAABBBCCDAA" * 5
        algo = get_algorithm("rle")
        legacy = build_compressed_bytes("rle", len(data), algo.compress(data))
        self.assertTrue(legacy.startswith(MAGIC_V1))
        restored, _ = decompress_file(legacy)
        self.assertEqual(restored, data)
        info = get_file_info(legacy)
        self.assertEqual(info["version"], 1)
        self.assertFalse(info["checksum_verified"])

    def test_info_reports_verified_checksum(self):
        data = b"some text some text some text"
        packed, _ = compress_file(data, algorithm="huffman")
        info = get_file_info(packed)
        self.assertEqual(info["version"], 2)
        self.assertTrue(info["checksum_verified"])
        self.assertEqual(info["original_size"], len(data))

    def test_truncated_file_is_rejected(self):
        packed, _ = compress_file(sample_inputs()["text"], algorithm="lz77h")
        with self.assertRaises(ValueError):
            decompress_file(packed[: len(packed) // 2])


if __name__ == "__main__":
    unittest.main()
