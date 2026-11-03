"""Huffman coding implementation.

This implementation builds a binary Huffman tree from byte frequencies,
serializes the tree into a compact bitstream, and stores encoded data bits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import heapq
from collections import Counter

from .base import CompressionAlgorithm, register_algorithm


@dataclass
class _Node:
    freq: int
    value: Optional[int] = None
    left: Optional["_Node"] = None
    right: Optional["_Node"] = None

    def is_leaf(self) -> bool:
        return self.value is not None


class _BitReader:
    def __init__(self, data: bytes, bit_count: int):
        if bit_count > len(data) * 8:
            raise ValueError("Unexpected end of bitstream.")
        self._data = data
        self._bit_count = bit_count
        self._pos = 0

    def read_bit(self) -> int:
        if self._pos >= self._bit_count:
            raise ValueError("Unexpected end of bitstream.")
        byte_index = self._pos // 8
        shift = 7 - (self._pos % 8)
        self._pos += 1
        return (self._data[byte_index] >> shift) & 1

    def read_bits(self, count: int) -> int:
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read_bit()
        return value


def _bits_to_bytes(bits: List[int]) -> bytes:
    if not bits:
        return b""
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (7 - (i % 8))
    return bytes(out)


def _build_tree(freqs: Dict[int, int]) -> Optional[_Node]:
    heap = []
    order = 0
    for value, freq in freqs.items():
        heapq.heappush(heap, (freq, order, _Node(freq=freq, value=value)))
        order += 1

    if not heap:
        return None
    if len(heap) == 1:
        return heap[0][2]

    while len(heap) > 1:
        f1, _, n1 = heapq.heappop(heap)
        f2, _, n2 = heapq.heappop(heap)
        parent = _Node(freq=f1 + f2, left=n1, right=n2)
        heapq.heappush(heap, (parent.freq, order, parent))
        order += 1

    return heap[0][2]


def _build_codes(node: _Node, prefix: List[int], codes: Dict[int, List[int]]) -> None:
    if node.is_leaf():
        codes[node.value] = prefix or [0]
        return
    _build_codes(node.left, prefix + [0], codes)
    _build_codes(node.right, prefix + [1], codes)


def _serialize_tree(node: _Node, bits: List[int]) -> None:
    if node.is_leaf():
        bits.append(1)
        value = node.value
        for i in range(7, -1, -1):
            bits.append((value >> i) & 1)
        return
    bits.append(0)
    _serialize_tree(node.left, bits)
    _serialize_tree(node.right, bits)


# A valid tree over 256 byte values is at most 255 levels deep; anything deeper
# means the stored tree is corrupt (and would otherwise recurse without limit).
_MAX_TREE_DEPTH = 256


def _deserialize_tree(reader: _BitReader, depth: int = 0) -> _Node:
    if depth > _MAX_TREE_DEPTH:
        raise ValueError("Invalid Huffman data; tree is too deep.")
    flag = reader.read_bit()
    if flag == 1:
        value = reader.read_bits(8)
        return _Node(freq=0, value=value)
    left = _deserialize_tree(reader, depth + 1)
    right = _deserialize_tree(reader, depth + 1)
    return _Node(freq=0, left=left, right=right)


def compress_bytes(data: bytes) -> bytes:
    """Compress bytes using Huffman coding."""
    if not data:
        return b""

    freqs = Counter(data)
    root = _build_tree(freqs)
    codes: Dict[int, List[int]] = {}
    _build_codes(root, [], codes)

    tree_bits: List[int] = []
    _serialize_tree(root, tree_bits)

    data_bits: List[int] = []
    for b in data:
        data_bits.extend(codes[b])

    tree_bits_len = len(tree_bits)
    data_bits_len = len(data_bits)
    header = tree_bits_len.to_bytes(4, "big") + data_bits_len.to_bytes(4, "big")

    return header + _bits_to_bytes(tree_bits) + _bits_to_bytes(data_bits)


def decompress_bytes(data: bytes) -> bytes:
    """Decompress Huffman-encoded bytes back to the original data."""
    if not data:
        return b""
    if len(data) < 8:
        raise ValueError("Invalid Huffman data; missing header.")

    tree_bits_len = int.from_bytes(data[0:4], "big")
    data_bits_len = int.from_bytes(data[4:8], "big")
    if tree_bits_len == 0:
        if data_bits_len != 0:
            raise ValueError("Invalid Huffman data; tree missing.")
        return b""

    tree_bytes_len = (tree_bits_len + 7) // 8
    if len(data) < 8 + tree_bytes_len:
        raise ValueError("Invalid Huffman data; incomplete tree.")

    tree_bytes = data[8 : 8 + tree_bytes_len]
    data_bytes = data[8 + tree_bytes_len :]

    tree_reader = _BitReader(tree_bytes, tree_bits_len)
    root = _deserialize_tree(tree_reader)

    if root.is_leaf():
        return bytes([root.value] * data_bits_len)

    data_reader = _BitReader(data_bytes, data_bits_len)
    out = bytearray()
    node = root
    for _ in range(data_bits_len):
        bit = data_reader.read_bit()
        node = node.left if bit == 0 else node.right
        if node.is_leaf():
            out.append(node.value)
            node = root

    return bytes(out)


def compress_string(text: str) -> str:
    """Compress a string and return hex-encoded Huffman bytes."""
    return compress_bytes(text.encode("utf-8")).hex()


def decompress_string(hex_data: str) -> str:
    """Decompress hex-encoded Huffman bytes back to a UTF-8 string."""
    return decompress_bytes(bytes.fromhex(hex_data)).decode("utf-8")


@register_algorithm("huffman")
class Huffman(CompressionAlgorithm):
    """Huffman algorithm wrapper for the shared interface."""

    def compress(self, data: bytes) -> bytes:
        return compress_bytes(data)

    def decompress(self, data: bytes) -> bytes:
        return decompress_bytes(data)
