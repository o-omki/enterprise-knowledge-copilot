from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    index: int


def chunk_text(text: str, source: str, chunk_size: int = 800) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(Chunk(text=text[start:end], source=source, index=idx))
        start = end
        idx += 1
    return chunks
