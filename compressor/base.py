from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Type


class CompressionAlgorithm(ABC):
    """Base interface for compression algorithms."""

    name: str = "base"

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress raw bytes into a compact representation."""
        raise NotImplementedError

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress bytes back to the original data."""
        raise NotImplementedError


_ALGORITHM_REGISTRY: Dict[str, Type[CompressionAlgorithm]] = {}


def register_algorithm(name: str):
    """Decorator to register an algorithm class by name."""

    def decorator(cls: Type[CompressionAlgorithm]) -> Type[CompressionAlgorithm]:
        if not issubclass(cls, CompressionAlgorithm):
            raise TypeError("Registered algorithm must inherit CompressionAlgorithm.")
        key = name.strip().lower()
        cls.name = key
        _ALGORITHM_REGISTRY[key] = cls
        return cls

    return decorator


def available_algorithms() -> List[str]:
    return sorted(_ALGORITHM_REGISTRY.keys())


def get_algorithm(name: str) -> CompressionAlgorithm:
    key = name.strip().lower()
    if key not in _ALGORITHM_REGISTRY:
        raise KeyError(f"Unknown algorithm: {name}")
    return _ALGORITHM_REGISTRY[key]()
