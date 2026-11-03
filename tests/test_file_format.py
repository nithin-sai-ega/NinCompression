import os
import sys
import tempfile
import unittest

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compressor import get_algorithm
from utils.file_format import (
    MAGIC,
    read_compressed_file,
    read_compressed_header,
    write_compressed_file,
)


class TestFileFormat(unittest.TestCase):
    def test_header_roundtrip(self):
        data = b"HELLOHELLOHELLO"
        algo = "rle"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample.nin")
            write_compressed_file(path, algo, len(data), data)

            with open(path, "rb") as f:
                raw = f.read()

            alg_len = raw[4]
            header_len = 4 + 1 + alg_len + 8
            self.assertTrue(raw.startswith(MAGIC))
            self.assertEqual(raw[5 : 5 + alg_len], algo.encode("utf-8"))
            self.assertEqual(len(raw[:header_len]), header_len)

            alg_read, size_read, payload = read_compressed_file(path)
            self.assertEqual(alg_read, algo)
            self.assertEqual(size_read, len(data))
            self.assertEqual(payload, data)

            alg_h, size_h, header_size = read_compressed_header(path)
            self.assertEqual(alg_h, algo)
            self.assertEqual(size_h, len(data))
            self.assertTrue(header_size > 0)

    def test_compress_write_read_decompress(self):
        original = b"AAAABBBCCDAA" + bytes([0, 1, 2, 255, 255])
        algo = get_algorithm("huffman")
        encoded = algo.compress(original)

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.nin")
            write_compressed_file(path, algo.name, len(original), encoded)
            alg_name, size, payload = read_compressed_file(path)
            self.assertEqual(size, len(original))
            decoded = get_algorithm(alg_name).decompress(payload)
            self.assertEqual(decoded, original)

    def test_invalid_magic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.nin")
            with open(path, "wb") as f:
                f.write(b"BAD1" + b"\x03rle" + (0).to_bytes(8, "big"))
            with self.assertRaises(ValueError):
                read_compressed_file(path)

    def test_corrupted_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "corrupt.nin")
            with open(path, "wb") as f:
                f.write(MAGIC + bytes([10]) + b"rle")
            with self.assertRaises(ValueError):
                read_compressed_file(path)

    def test_unknown_algorithm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "unknown.nin")
            with open(path, "wb") as f:
                f.write(MAGIC + b"\x07unknown" + (0).to_bytes(8, "big"))
            with self.assertRaises(ValueError):
                read_compressed_file(path)

    def test_empty_file(self):
        algo = get_algorithm("rle")
        original = b""
        encoded = algo.compress(original)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.nin")
            write_compressed_file(path, algo.name, len(original), encoded)
            alg_name, size, payload = read_compressed_file(path)
            decoded = get_algorithm(alg_name).decompress(payload)
            self.assertEqual(size, 0)
            self.assertEqual(decoded, original)

    def test_binary_file(self):
        algo = get_algorithm("huffman")
        original = bytes(range(256))
        encoded = algo.compress(original)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "binary.nin")
            write_compressed_file(path, algo.name, len(original), encoded)
            alg_name, size, payload = read_compressed_file(path)
            decoded = get_algorithm(alg_name).decompress(payload)
            self.assertEqual(size, len(original))
            self.assertEqual(decoded, original)


if __name__ == "__main__":
    unittest.main()
