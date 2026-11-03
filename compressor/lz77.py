"""LZ77 compression implementation with a sliding window.

Matches are found with a hash table keyed on the next three bytes, so each
position only looks at a handful of earlier positions that start with the same
three bytes instead of scanning the whole window. The token format is unchanged.
"""

from __future__ import annotations

from .base import CompressionAlgorithm, register_algorithm

SEARCH_BUFFER_SIZE = 4096
LOOKAHEAD_BUFFER_SIZE = 18
MIN_MATCH_LENGTH = 3
DEFAULT_LEVEL = 3
MIN_LEVEL = 1
MAX_LEVEL = 5

# How many earlier positions are checked per input position at each level.
# Higher levels check more candidates: slower, but they find longer matches.
_CHAIN_LIMIT = {1: 8, 2: 16, 3: 32, 4: 64, 5: 128}


def _encode_token(offset: int, length: int, has_next: bool, next_byte: int) -> bytes:
    if offset < 0 or offset > SEARCH_BUFFER_SIZE:
        raise ValueError("Invalid LZ77 offset.")
    if length < 0 or length > LOOKAHEAD_BUFFER_SIZE:
        raise ValueError("Invalid LZ77 length.")
    if next_byte < 0 or next_byte > 255:
        raise ValueError("Invalid LZ77 next_byte.")

    flag_length = (0x80 if has_next else 0x00) | (length & 0x7F)
    return offset.to_bytes(2, "big") + bytes([flag_length, next_byte])


def _decode_token(token: bytes) -> tuple[int, int, bool, int]:
    if len(token) != 4:
        raise ValueError("Invalid LZ77 token length.")
    offset = int.from_bytes(token[0:2], "big")
    flag_length = token[2]
    has_next = (flag_length & 0x80) != 0
    length = flag_length & 0x7F
    next_byte = token[3]
    return offset, length, has_next, next_byte


def _check_level(level: int) -> None:
    if level < MIN_LEVEL or level > MAX_LEVEL:
        raise ValueError(f"LZ77 level must be between {MIN_LEVEL} and {MAX_LEVEL}.")


def _level_to_search_limit(level: int) -> int:
    _check_level(level)
    # Lower levels search a smaller window for speed; higher levels search more.
    scaled = int(SEARCH_BUFFER_SIZE * (level / MAX_LEVEL))
    return max(64, min(SEARCH_BUFFER_SIZE, scaled))


def _find_longest_match(
    data: bytes,
    pos: int,
    search_limit: int,
    table: dict[bytes, list[int]],
    chain_limit: int,
) -> tuple[int, int]:
    """Find the longest match for the bytes at ``pos``.

    Returns (offset, length). Offset is how far back the match starts, and
    length is 0 when nothing of at least MIN_MATCH_LENGTH was found.
    """
    end = min(pos + LOOKAHEAD_BUFFER_SIZE, len(data))
    best_length = 0
    best_offset = 0

    candidates = table.get(data[pos : pos + MIN_MATCH_LENGTH])
    if not candidates:
        return 0, 0

    # Candidates are stored oldest to newest; check the newest (closest) first.
    checked = 0
    for idx in range(len(candidates) - 1, -1, -1):
        j = candidates[idx]
        if pos - j > search_limit or checked >= chain_limit:
            break
        checked += 1

        length = 0
        while pos + length < end and data[j + length] == data[pos + length]:
            length += 1
        if length > best_length:
            best_length = length
            best_offset = pos - j
            if pos + best_length == end:
                break

    return best_offset, best_length


def _remember(data: bytes, pos: int, table: dict[bytes, list[int]]) -> None:
    """Record that the three bytes starting at ``pos`` occur there."""
    if pos + MIN_MATCH_LENGTH <= len(data):
        table.setdefault(data[pos : pos + MIN_MATCH_LENGTH], []).append(pos)


def compress_bytes(data: bytes, level: int = DEFAULT_LEVEL) -> bytes:
    """Compress bytes using LZ77."""
    if not data:
        _check_level(level)
        return b""

    search_limit = _level_to_search_limit(level)
    chain_limit = _CHAIN_LIMIT[level]
    table: dict[bytes, list[int]] = {}
    out = bytearray()
    i = 0
    while i < len(data):
        offset, length = _find_longest_match(data, i, search_limit, table, chain_limit)

        if length >= MIN_MATCH_LENGTH:
            has_next = (i + length) < len(data)
            next_byte = data[i + length] if has_next else 0
            out.extend(_encode_token(offset, length, has_next, next_byte))
            consumed = length + (1 if has_next else 0)
        else:
            out.extend(_encode_token(0, 0, True, data[i]))
            consumed = 1

        for p in range(i, i + consumed):
            _remember(data, p, table)
        i += consumed

    return bytes(out)


def decompress_bytes(data: bytes) -> bytes:
    """Decompress LZ77-encoded bytes back to the original data."""
    if not data:
        return b""
    if len(data) % 4 != 0:
        raise ValueError("Invalid LZ77 data length; expected 4-byte tokens.")

    out = bytearray()
    for i in range(0, len(data), 4):
        offset, length, has_next, next_byte = _decode_token(data[i : i + 4])
        if length > 0:
            if offset == 0 or offset > len(out):
                raise ValueError("Invalid LZ77 offset in token.")
            start = len(out) - offset
            for _ in range(length):
                out.append(out[start])
                start += 1
        if has_next:
            out.append(next_byte)

    return bytes(out)


def compress_string(text: str, level: int = DEFAULT_LEVEL) -> str:
    """Compress a string and return hex-encoded LZ77 bytes."""
    return compress_bytes(text.encode("utf-8"), level=level).hex()


def decompress_string(hex_data: str) -> str:
    """Decompress hex-encoded LZ77 bytes back to a UTF-8 string."""
    return decompress_bytes(bytes.fromhex(hex_data)).decode("utf-8")


@register_algorithm("lz77")
class LZ77(CompressionAlgorithm):
    """LZ77 algorithm wrapper for the shared interface."""

    def __init__(self, level: int = DEFAULT_LEVEL) -> None:
        _check_level(level)
        self.level = level

    def compress(self, data: bytes) -> bytes:
        return compress_bytes(data, level=self.level)

    def decompress(self, data: bytes) -> bytes:
        return decompress_bytes(data)
