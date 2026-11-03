"""The .nin container format.

Version 2 (written by default):
    [NIN2][alg_len][alg_name][original_size][crc32][compressed_data]

Version 1 (still readable, has no integrity check):
    [NIN1][alg_len][alg_name][original_size][compressed_data]

- magic: 4 bytes, "NIN2" or "NIN1"
- alg_len: 1 byte (1..255)
- alg_name: UTF-8 bytes
- original_size: 8-byte unsigned big-endian
- crc32: 4-byte unsigned big-endian CRC-32 of the *original* data (version 2 only)
"""

from __future__ import annotations

import zlib
from typing import NamedTuple, Optional

MAGIC_V1 = b"NIN1"
MAGIC_V2 = b"NIN2"
# Kept for backward compatibility: the original name referred to version 1.
MAGIC = MAGIC_V1

_SIZE_BYTES = 8
_CRC_BYTES = 4


class Container(NamedTuple):
    """The parsed pieces of a .nin file."""

    version: int
    algorithm: str
    original_size: int
    crc32: Optional[int]
    header_size: int
    payload: bytes


def crc32_of(data: bytes) -> int:
    """CRC-32 of ``data`` as an unsigned integer."""
    return zlib.crc32(data) & 0xFFFFFFFF


def _validate_algorithm(algorithm: str) -> bytes:
    alg_bytes = algorithm.encode("utf-8")
    if len(alg_bytes) == 0:
        raise ValueError("Algorithm name cannot be empty.")
    if len(alg_bytes) > 255:
        raise ValueError("Algorithm name too long for header.")
    from compressor import available_algorithms

    if algorithm.strip().lower() not in available_algorithms():
        raise ValueError(f"Unknown algorithm: {algorithm}")
    return alg_bytes


def parse_container(data: bytes) -> Container:
    """Parse a .nin file held in memory. Raises ValueError if it is invalid."""
    if len(data) < 4 + 1 + _SIZE_BYTES:
        raise ValueError("Invalid file; header too short.")

    magic = data[:4]
    if magic == MAGIC_V2:
        version, crc_len = 2, _CRC_BYTES
    elif magic == MAGIC_V1:
        version, crc_len = 1, 0
    else:
        raise ValueError("Invalid file; magic bytes not found.")

    alg_len = data[4]
    if alg_len == 0:
        raise ValueError("Invalid file; algorithm name is empty.")
    header_len = 4 + 1 + alg_len + _SIZE_BYTES + crc_len
    if len(data) < header_len:
        raise ValueError("Invalid file; header incomplete.")

    alg_start = 5
    alg_end = alg_start + alg_len
    try:
        alg_name = data[alg_start:alg_end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid file; algorithm name is not valid UTF-8.") from exc

    size_end = alg_end + _SIZE_BYTES
    original_size = int.from_bytes(data[alg_end:size_end], "big")
    crc = int.from_bytes(data[size_end : size_end + crc_len], "big") if crc_len else None

    from compressor import available_algorithms

    if alg_name.strip().lower() not in available_algorithms():
        raise ValueError(f"Unknown algorithm in file: {alg_name}")

    return Container(version, alg_name, original_size, crc, header_len, data[header_len:])


def build_compressed_bytes(
    algorithm: str,
    original_size: int,
    compressed_data: bytes,
    crc32: Optional[int] = None,
) -> bytes:
    """Build a .nin file in memory.

    With ``crc32`` (the CRC-32 of the original data) a version 2 file is built;
    without it, a version 1 file.
    """
    if original_size < 0 or original_size >= 1 << 64:
        raise ValueError("original_size must fit in an unsigned 8-byte integer.")
    alg_bytes = _validate_algorithm(algorithm)

    if crc32 is None:
        magic, crc_bytes = MAGIC_V1, b""
    else:
        if crc32 < 0 or crc32 >= 1 << 32:
            raise ValueError("crc32 must fit in an unsigned 4-byte integer.")
        magic, crc_bytes = MAGIC_V2, crc32.to_bytes(_CRC_BYTES, "big")

    header = (
        magic
        + bytes([len(alg_bytes)])
        + alg_bytes
        + original_size.to_bytes(_SIZE_BYTES, "big")
        + crc_bytes
    )
    return header + compressed_data


def verify_original(container: Container, original: bytes) -> None:
    """Check decompressed data against the stored size and checksum."""
    if len(original) != container.original_size:
        raise ValueError(
            f"Size mismatch after decompression: expected {container.original_size}, "
            f"got {len(original)}."
        )
    if container.crc32 is not None and crc32_of(original) != container.crc32:
        raise ValueError("Checksum mismatch; the file is corrupted.")


def write_compressed_file(
    path: str,
    algorithm: str,
    original_size: int,
    compressed_data: bytes,
    crc32: Optional[int] = None,
) -> None:
    """Write a compressed file with the header described at the top of this module."""
    with open(path, "wb") as f:
        f.write(build_compressed_bytes(algorithm, original_size, compressed_data, crc32))


def read_compressed_header(path: str) -> tuple[str, int, int]:
    """Read only the header and return (algorithm, original_size, header_size)."""
    with open(path, "rb") as f:
        prefix = f.read(5)
        if len(prefix) < 5:
            raise ValueError("Invalid file; header too short.")
        rest = f.read(prefix[4] + _SIZE_BYTES + _CRC_BYTES)
    parsed = parse_container(prefix + rest)
    return parsed.algorithm, parsed.original_size, parsed.header_size


def read_compressed_header_bytes(data: bytes) -> tuple[str, int, int]:
    """Read only the header from in-memory bytes."""
    parsed = parse_container(data)
    return parsed.algorithm, parsed.original_size, parsed.header_size


def read_container(path: str) -> Container:
    """Read and parse a .nin file from disk."""
    with open(path, "rb") as f:
        return parse_container(f.read())


def read_compressed_file(path: str) -> tuple[str, int, bytes]:
    """Read a compressed file and return (algorithm, original_size, data)."""
    parsed = read_container(path)
    return parsed.algorithm, parsed.original_size, parsed.payload


def read_compressed_file_bytes(data: bytes) -> tuple[str, int, bytes]:
    """Read a compressed file from in-memory bytes."""
    parsed = parse_container(data)
    return parsed.algorithm, parsed.original_size, parsed.payload
