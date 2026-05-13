from __future__ import annotations

from src.schema import RetrievalResult


def summarize_evidence(results: list[RetrievalResult], limit: int = 2) -> list[str]:
    summaries = []
    for result in results[:limit]:
        summaries.append(f"{result.chunk.text} [{result.chunk.citation}]")
    return summaries

