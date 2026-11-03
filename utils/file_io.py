from __future__ import annotations


def read_binary(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def write_binary(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
