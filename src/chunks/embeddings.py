from __future__ import annotations

import math
from collections import Counter

from src.schema import Chunk
from src.utils import tokenize


class LightweightVectorIndex:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.doc_freq: Counter[str] = Counter()
        self.chunk_vectors: dict[str, Counter[str]] = {}
        self._build()

    def _build(self) -> None:
        for chunk in self.chunks:
            counts = Counter(tokenize(chunk.text))
            self.chunk_vectors[chunk.chunk_id] = counts
            for token in counts:
                self.doc_freq[token] += 1

    def tfidf(self, counts: Counter[str]) -> Counter[str]:
        total_docs = max(len(self.chunks), 1)
        vector: Counter[str] = Counter()
        for token, count in counts.items():
            idf = math.log((1 + total_docs) / (1 + self.doc_freq.get(token, 0))) + 1
            vector[token] = count * idf
        return vector

