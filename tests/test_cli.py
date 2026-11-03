import os
import subprocess
import sys
import tempfile
import unittest

from helpers import PROJECT_ROOT, sample_inputs


def run_cli(*args):
    return subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "main.py"), *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


class TestCli(unittest.TestCase):
    def test_file_roundtrip_for_every_algorithm(self):
        data = sample_inputs()["text"]
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.bin")
            with open(src, "wb") as f:
                f.write(data)
            for algo in ("auto", "rle", "huffman", "lz77", "lz77h", "store"):
                with self.subTest(algo):
                    packed = os.path.join(tmp, f"{algo}.nin")
                    restored = os.path.join(tmp, f"{algo}.out")
                    self.assertEqual(run_cli("compress", "-a", algo, src, packed).returncode, 0)
                    self.assertEqual(run_cli("decompress", packed, restored).returncode, 0)
                    with open(restored, "rb") as f:
                        self.assertEqual(f.read(), data)

    def test_info_shows_verified_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.txt")
            packed = os.path.join(tmp, "in.nin")
            with open(src, "wb") as f:
                f.write(b"abc abc abc abc abc")
            run_cli("compress", src, packed)
            result = run_cli("info", packed)
            self.assertEqual(result.returncode, 0)
            self.assertIn("verified", result.stdout)

    def test_missing_file_gives_clean_error(self):
        result = run_cli("compress", "does_not_exist.txt", "out.nin")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("error:"))
        self.assertNotIn("Traceback", result.stderr)

    def test_bad_file_gives_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "plain.txt")
            with open(src, "wb") as f:
                f.write(b"this is not a .nin file")
            result = run_cli("decompress", src, os.path.join(tmp, "out"))
            self.assertEqual(result.returncode, 1)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_level_out_of_range_is_rejected(self):
        result = run_cli("compress-string", "-a", "lz77", "--level", "9", "hello")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("level must be between", result.stderr)

    def test_string_roundtrip(self):
        for algo in ("rle", "huffman", "lz77", "lz77h"):
            with self.subTest(algo):
                hex_out = run_cli("compress-string", "-a", algo, "AAABBBCCDAA AAABBB").stdout.strip()
                back = run_cli("decompress-string", "-a", algo, hex_out)
                self.assertEqual(back.stdout.strip(), "AAABBBCCDAA AAABBB")


if __name__ == "__main__":
    unittest.main()
