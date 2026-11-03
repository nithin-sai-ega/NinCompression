"""Shared helpers for the test suite."""

import os
import random
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def sample_inputs(seed: int = 1234):
    """A mix of inputs that exercises every algorithm: empty, tiny, runs, text, random."""
    rng = random.Random(seed)
    words = b"the quick brown fox jumps over the lazy dog and keeps running".split()
    text = b" ".join(rng.choice(words) for _ in range(400))
    runs = b"".join(bytes([rng.getrandbits(8)]) * rng.randint(1, 300) for _ in range(40))
    return {
        "empty": b"",
        "one byte": b"x",
        "same byte": b"z" * 1000,
        "text": text,
        "runs": runs,
        "random": bytes(rng.getrandbits(8) for _ in range(3000)),
        "all byte values": bytes(range(256)) * 3,
    }
