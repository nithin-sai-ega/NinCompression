"""Hybrid LZ77 + Huffman compression pipeline."""

from __future__ import annotations

from .base import CompressionAlgorithm, register_algorithm
from .lz77 import (
    DEFAULT_LEVEL,
    _check_level,
    compress_bytes as lz77_compress,
    decompress_bytes as lz77_decompress,
)
from .huffman import (
    compress_bytes as huffman_compress,
    decompress_bytes as huffman_decompress,
)


@register_algorithm("lz77h")
class LZ77Huffman(CompressionAlgorithm):
    """LZ77 followed by Huffman coding."""

    def __init__(self, level: int = DEFAULT_LEVEL) -> None:
        _check_level(level)
        self.level = level

    def compress(self, data: bytes) -> bytes:
        lz77_data = lz77_compress(data, level=self.level)
        return huffman_compress(lz77_data)

    def decompress(self, data: bytes) -> bytes:
        lz77_data = huffman_decompress(data)
        return lz77_decompress(lz77_data)
