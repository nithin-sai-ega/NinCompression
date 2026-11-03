from .base import (
    CompressionAlgorithm,
    available_algorithms,
    get_algorithm,
    register_algorithm,
)
from .rle import (
    RLE,
    compress_bytes as rle_compress_bytes,
    decompress_bytes as rle_decompress_bytes,
    compress_string as rle_compress_string,
    decompress_string as rle_decompress_string,
)

# Import algorithms to ensure registration on package import.
from . import rle as _rle  # noqa: F401
from . import huffman as _huffman  # noqa: F401
from . import lz77 as _lz77  # noqa: F401
from . import lz77_huffman as _lz77_huffman  # noqa: F401
from . import store as _store  # noqa: F401

__all__ = [
    "CompressionAlgorithm",
    "available_algorithms",
    "get_algorithm",
    "register_algorithm",
    "RLE",
    "rle_compress_bytes",
    "rle_decompress_bytes",
    "rle_compress_string",
    "rle_decompress_string",
]
