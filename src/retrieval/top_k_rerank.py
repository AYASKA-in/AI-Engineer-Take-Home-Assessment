from __future__ import annotations

import re

from src.schema import Chunk


ENTITY_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b|\b\d{4}\b")
DATE_QUERY_TERMS = {"date", "timeline", "chronology", "deadline", "signed", "schedule", "when", "time"}


def rerank_bonus(query: str, chunk: Chunk) -> float:
    lowered = chunk.text.lower()
    query_lower = query.lower()
    bonus = 0.0
    if "section" in query_lower and "section" in lowered:
        bonus += 0.08
    if any(char.isdigit() for char in query) and any(char.isdigit() for char in chunk.text):
        bonus += 0.05
    entities = ENTITY_RE.findall(query)
    if any(entity.lower() in lowered for entity in entities):
        bonus += 0.07
    query_tokens = set(query_lower.split())
    if query_tokens & DATE_QUERY_TERMS and DATE_RE.search(chunk.text):
        bonus += 0.06
    if chunk.confidence < 0.6:
        bonus -= 0.05
    return bonus

