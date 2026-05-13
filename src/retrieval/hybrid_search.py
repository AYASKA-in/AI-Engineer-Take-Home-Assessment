from __future__ import annotations

from collections import Counter

from src.chunks.embeddings import LightweightVectorIndex
from src.retrieval.top_k_rerank import rerank_bonus
from src.schema import Chunk, RetrievalResult
from src.utils import cosine_similarity, tokenize


class HybridSearch:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.index = LightweightVectorIndex(chunks)

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        query_counts = Counter(tokenize(query))
        query_vector = self.index.tfidf(query_counts)
        results: list[RetrievalResult] = []
        query_terms = set(query_counts)

        for chunk in self.chunks:
            chunk_counts = self.index.chunk_vectors[chunk.chunk_id]
            lexical_hits = query_terms & set(chunk_counts)
            lexical_score = len(lexical_hits) / max(len(query_terms), 1)
            semantic_score = cosine_similarity(query_vector, self.index.tfidf(chunk_counts))
            rerank_score = rerank_bonus(query, chunk)
            score = (0.55 * lexical_score) + (0.35 * semantic_score) + rerank_score + (0.10 * chunk.confidence)
            if score <= 0:
                continue
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                    lexical_score=lexical_score,
                    semantic_score=semantic_score,
                    rerank_score=rerank_score,
                    matched_terms=sorted(lexical_hits),
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

