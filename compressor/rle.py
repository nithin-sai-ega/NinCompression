"""Run-Length Encoding (RLE) implementation.

RLE replaces runs of the same byte with (count, byte) pairs.
This implementation stores count as a single byte (1..255).
"""

from __future__ import annotations

from .base import CompressionAlgorithm, register_algorithm


def compress_bytes(data: bytes) -> bytes:
    """Compress bytes using RLE.

    Output format: [count][byte][count][byte]...
    Count is 1..255, so long runs are split across multiple pairs.
    """
    if not data:
        return b""

    out = bytearray()
    current = data[0]
    count = 1

    for b in data[1:]:
        if b == current and count < 255:
            count += 1
        else:
            out.append(count)
            out.append(current)
            current = b
            count = 1

    out.append(count)
    out.append(current)
    return bytes(out)


def decompress_bytes(data: bytes) -> bytes:
    """Decompress RLE-encoded bytes back to the original data."""
    if not data:
        return b""
    if len(data) % 2 != 0:
        raise ValueError("Invalid RLE data length; expected count/byte pairs.")

    out = bytearray()
    it = iter(data)
    for count in it:
        value = next(it)
        if count == 0:
            raise ValueError("Invalid RLE count of 0.")
        out.extend([value] * count)

    return bytes(out)


def compress_string(text: str) -> str:
    """Compress a string and return hex-encoded RLE bytes."""
    raw = text.encode("utf-8")
    return compress_bytes(raw).hex()


def decompress_string(hex_data: str) -> str:
    """Decompress hex-encoded RLE bytes back to a UTF-8 string."""
    raw = bytes.fromhex(hex_data)
    return decompress_bytes(raw).decode("utf-8")


@register_algorithm("rle")
class RLE(CompressionAlgorithm):
    """RLE algorithm wrapper for the shared interface."""

    def compress(self, data: bytes) -> bytes:
        return compress_bytes(data)

    def decompress(self, data: bytes) -> bytes:
        return decompress_bytes(data)
