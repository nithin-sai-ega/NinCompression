from __future__ import annotations

import argparse
import os
import sys
import time

from compressor import CompressionAlgorithm, available_algorithms, get_algorithm
from compressor.lz77 import DEFAULT_LEVEL, LZ77, MAX_LEVEL, MIN_LEVEL
from compressor.lz77_huffman import LZ77Huffman
from utils.file_io import read_binary, write_binary
from utils.file_format import (
    build_compressed_bytes,
    crc32_of,
    parse_container,
    read_container,
    verify_original,
    write_compressed_file,
)

AUTO = "auto"
# Algorithms that "auto" tries. The smallest result wins; if none beats the
# raw data, the input is stored unchanged.
AUTO_CANDIDATES = ("rle", "huffman", "lz77", "lz77h")


def make_algorithm(name: str, level: int = DEFAULT_LEVEL) -> CompressionAlgorithm:
    """Build an algorithm by registry name; ``level`` applies to the LZ77 family."""
    key = name.strip().lower()
    if key == "lz77":
        return LZ77(level=level)
    if key == "lz77h":
        return LZ77Huffman(level=level)
    return get_algorithm(key)


def choose_best(data: bytes, level: int = DEFAULT_LEVEL) -> tuple[CompressionAlgorithm, bytes]:
    """Try every candidate and return the one with the smallest output."""
    best_algo = make_algorithm("store")
    best_payload = best_algo.compress(data)
    for name in AUTO_CANDIDATES:
        algo = make_algorithm(name, level)
        payload = algo.compress(data)
        # Compare payload sizes; the algorithm name in the header differs by a
        # few bytes, which is not worth a different choice.
        if len(payload) < len(best_payload):
            best_algo, best_payload = algo, payload
    return best_algo, best_payload


def compress_data(
    data: bytes, algorithm: str = AUTO, level: int = DEFAULT_LEVEL
) -> tuple[str, bytes]:
    """Compress raw bytes and return (algorithm_name, payload)."""
    if algorithm.strip().lower() == AUTO:
        algo, payload = choose_best(data, level)
    else:
        algo = make_algorithm(algorithm, level)
        payload = algo.compress(data)
    return algo.name, payload


def compress_file(
    input_bytes: bytes,
    algorithm: str = AUTO,
    level: int = DEFAULT_LEVEL,
    output_format: str = "nin",
) -> tuple[bytes, str]:
    """Compress raw bytes and return (output_bytes, filename).

    - algorithm: registry name (rle, huffman, lz77, lz77h, store) or "auto"
    - level: LZ77 compression level 1-5 (used by lz77, lz77h and auto)
    - output_format: currently supports only "nin"
    """
    if output_format != "nin":
        raise ValueError("Only 'nin' output_format is supported.")

    name, payload = compress_data(input_bytes, algorithm, level)
    output_bytes = build_compressed_bytes(
        name, len(input_bytes), payload, crc32=crc32_of(input_bytes)
    )
    return output_bytes, f"output.{output_format}"


def decompress_file(input_bytes: bytes) -> tuple[bytes, str]:
    """Decompress raw .nin bytes and return (output_bytes, filename)."""
    container = parse_container(input_bytes)
    raw = get_algorithm(container.algorithm).decompress(container.payload)
    verify_original(container, raw)
    return raw, "restored.bin"


def get_file_info(input_bytes: bytes) -> dict:
    """Return metadata about a .nin payload as a dictionary."""
    container = parse_container(input_bytes)
    compressed_size = len(input_bytes)
    original_size = container.original_size
    ratio = (compressed_size / original_size) if original_size > 0 else 0.0

    # Decompress (timed) so the checksum and size can be verified as well.
    algo = get_algorithm(container.algorithm)
    t0 = time.perf_counter()
    raw = algo.decompress(container.payload)
    t1 = time.perf_counter()
    verify_original(container, raw)

    return {
        "version": container.version,
        "algorithm": container.algorithm,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "ratio": ratio,
        "decompression_time": t1 - t0,
        "header_size": container.header_size,
        "crc32": container.crc32,
        "checksum_verified": container.crc32 is not None,
    }


def _level_arg(value: str) -> int:
    try:
        level = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid level: {value!r}") from exc
    if not MIN_LEVEL <= level <= MAX_LEVEL:
        raise argparse.ArgumentTypeError(
            f"level must be between {MIN_LEVEL} and {MAX_LEVEL}"
        )
    return level


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="NinCompression: RLE, Huffman, LZ77 and LZ77+Huffman compression.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    algo_choices = available_algorithms()
    file_choices = algo_choices + [AUTO]

    def add_level(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--level",
            type=_level_arg,
            default=DEFAULT_LEVEL,
            help=f"LZ77 level {MIN_LEVEL}-{MAX_LEVEL} for lz77/lz77h/auto "
            f"(default: {DEFAULT_LEVEL})",
        )

    p_compress = sub.add_parser("compress", help="Compress a file")
    p_compress.add_argument("input", help="Input file path")
    p_compress.add_argument("output", help="Output file path")
    p_compress.add_argument(
        "--algorithm",
        "-a",
        default=AUTO,
        choices=file_choices,
        help="Compression algorithm (default: auto, which keeps the smallest result)",
    )
    add_level(p_compress)

    p_decompress = sub.add_parser("decompress", help="Decompress a file")
    p_decompress.add_argument("input", help="Input file path")
    p_decompress.add_argument("output", help="Output file path")

    p_cstr = sub.add_parser("compress-string", help="Compress a string to hex")
    p_cstr.add_argument("text", help="String to compress")
    p_cstr.add_argument(
        "--algorithm",
        "-a",
        default="rle",
        choices=algo_choices,
        help="Compression algorithm (default: rle)",
    )
    add_level(p_cstr)

    p_dstr = sub.add_parser("decompress-string", help="Decompress a hex string")
    p_dstr.add_argument("hex_data", help="Hex-encoded compressed data")
    p_dstr.add_argument(
        "--algorithm",
        "-a",
        default="rle",
        choices=algo_choices,
        help="Algorithm the string was compressed with (default: rle)",
    )

    p_info = sub.add_parser("info", help="Inspect a .nin file and verify it")
    p_info.add_argument("input", help="Input .nin file path")

    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "compress":
        raw = read_binary(args.input)
        name, payload = compress_data(raw, args.algorithm, args.level)
        write_compressed_file(args.output, name, len(raw), payload, crc32=crc32_of(raw))
        total = os.path.getsize(args.output)
        pct = (100.0 * total / len(raw)) if raw else 0.0
        print(f"{args.input} -> {args.output}  [{name}]  {len(raw)} -> {total} bytes ({pct:.1f}%)")
        return 0

    if args.command == "decompress":
        container = read_container(args.input)
        raw = get_algorithm(container.algorithm).decompress(container.payload)
        verify_original(container, raw)
        write_binary(args.output, raw)
        print(f"{args.input} -> {args.output}  [{container.algorithm}]  {len(raw)} bytes")
        return 0

    if args.command == "compress-string":
        algo = make_algorithm(args.algorithm, args.level)
        print(algo.compress(args.text.encode("utf-8")).hex())
        return 0

    if args.command == "decompress-string":
        algo = get_algorithm(args.algorithm)
        print(algo.decompress(bytes.fromhex(args.hex_data)).decode("utf-8"))
        return 0

    if args.command == "info":
        info = get_file_info(read_binary(args.input))
        print(f"Format version: NIN{info['version']}")
        print(f"Algorithm: {info['algorithm']}")
        print(f"Original size: {info['original_size']} bytes")
        print(f"Compressed size: {info['compressed_size']} bytes")
        print(f"Compression ratio: {info['ratio']:.3f}")
        print(f"Decompression time: {info['decompression_time']:.4f}s")
        if info["checksum_verified"]:
            print(f"Checksum: CRC-32 {info['crc32']:08x} verified")
        else:
            print("Checksum: none (NIN1 files have no checksum)")
        return 0

    return 1


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except KeyError as exc:
        message = exc.args[0] if exc.args else exc
        print(f"error: {message}", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
