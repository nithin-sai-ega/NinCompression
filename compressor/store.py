"""Store (no compression).

Keeps the data as-is. It is the fallback used by ``auto`` mode when none of the
real algorithms makes the data smaller (for example, already-compressed or
random data), so a file never grows by more than the container header.
"""

from __future__ import annotations

from .base import CompressionAlgorithm, register_algorithm


@register_algorithm("store")
class Store(CompressionAlgorithm):
    """Identity 'algorithm' that stores bytes unchanged."""

    def compress(self, data: bytes) -> bytes:
        return bytes(data)

    def decompress(self, data: bytes) -> bytes:
        return bytes(data)
