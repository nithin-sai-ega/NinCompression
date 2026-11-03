import argparse
import csv
import os
import random
import sys
import time
import zlib

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compressor import get_algorithm, available_algorithms


def _dataset_sample_text() -> bytes:
    return (b"the quick brown fox jumps over the lazy dog " * 200)


def _dataset_words() -> bytes:
    """Pseudo-random words from a small vocabulary: more realistic than one repeated sentence."""
    rng = random.Random(2024)
    vocab = (
        "the of and to in is that for it as was with be by on not he this are or his "
        "from at which but have an had they you were their one all we can her has there "
        "been if more when will would who so no data file byte stream compress window"
    ).split()
    out = bytearray()
    while len(out) < 30000:
        out += rng.choice(vocab).encode() + b" "
    return bytes(out[:30000])


def _dataset_repeating() -> bytes:
    return (b"ABCD" * 2000)


def _dataset_random_binary() -> bytes:
    rng = random.Random(12345)
    return bytes(rng.getrandbits(8) for _ in range(4096))


def _print_table(title: str, rows: list[tuple[str, int, float, float, float]]) -> None:
    print(title)
    print("Algorithm          Size(bytes)   Ratio   Compress(ms)   Decompress(ms)")
    for name, size, ratio, c_ms, d_ms in rows:
        print(f"{name:<17} {size:>10}   {ratio:>5.2f}   {c_ms:>11.2f}   {d_ms:>13.2f}")
    print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark compression algorithms.")
    parser.add_argument(
        "--dataset",
        choices=["text", "words", "repeating", "binary"],
        help="Run benchmarks for a specific dataset only.",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Write benchmark results to a CSV file.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    algos = [
        a for a in available_algorithms() if a in {"rle", "huffman", "lz77", "lz77h"}
    ]
    if not algos:
        print("No algorithms available for benchmarking.")
        return 1

    datasets_all = [
        ("text", "Sample Text", _dataset_sample_text()),
        ("words", "Random Words", _dataset_words()),
        ("repeating", "Repeating Data", _dataset_repeating()),
        ("binary", "Random Binary", _dataset_random_binary()),
    ]
    if args.dataset:
        datasets = [d for d in datasets_all if d[0] == args.dataset]
    else:
        datasets = datasets_all

    csv_rows: list[tuple[str, str, int, float, float, float]] = []

    for key, label, data in datasets:
        rows: list[tuple[str, int, float, float, float]] = []
        for name in algos:
            algo = get_algorithm(name)

            t0 = time.perf_counter()
            compressed = algo.compress(data)
            t1 = time.perf_counter()

            t2 = time.perf_counter()
            decompressed = algo.decompress(compressed)
            t3 = time.perf_counter()

            if decompressed != data:
                raise ValueError(f"Benchmark failed; {name} round-trip mismatch.")

            ratio = (len(compressed) / len(data)) if len(data) else 0.0
            c_ms = (t1 - t0) * 1000.0
            d_ms = (t3 - t2) * 1000.0

            display = "LZ77+Huffman" if name == "lz77h" else name.upper()
            rows.append((display, len(compressed), ratio, c_ms, d_ms))
            csv_rows.append((key, display, len(compressed), ratio, c_ms, d_ms))

        # zlib is only here as a yardstick; none of the algorithms above use it.
        t0 = time.perf_counter()
        reference = zlib.compress(data, 9)
        t1 = time.perf_counter()
        zlib.decompress(reference)
        t2 = time.perf_counter()
        ref_ratio = (len(reference) / len(data)) if len(data) else 0.0
        rows.append(("zlib (reference)", len(reference), ref_ratio, (t1 - t0) * 1000.0, (t2 - t1) * 1000.0))
        csv_rows.append((key, "zlib (reference)", len(reference), ref_ratio, (t1 - t0) * 1000.0, (t2 - t1) * 1000.0))

        _print_table(f"Dataset: {label} (input {len(data)} bytes)", rows)

    if args.csv_path:
        with open(args.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "dataset",
                    "algorithm",
                    "compressed_size",
                    "ratio",
                    "compress_ms",
                    "decompress_ms",
                ]
            )
            for row in csv_rows:
                writer.writerow(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
