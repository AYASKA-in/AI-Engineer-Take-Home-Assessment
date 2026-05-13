from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.schema import (
    ConfidenceTier,
    ExtractedDocument,
    LineRecord,
    classify_confidence,
)
from src.utils import normalize_whitespace

UNCLEAR_TOKENS = {"[illegible]", "??", "unclear", "redacted", "[unreadable]", "???"}


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, path: str | Path) -> ExtractedDocument:
        raise NotImplementedError

    def _build_lines(self, text: str, confidence: float) -> list[LineRecord]:
        pages = [page.strip("\n") for page in text.split("\f")]
        lines: list[LineRecord] = []
        for page_num, page_text in enumerate(pages, start=1):
            raw_lines = [line for line in page_text.splitlines() if line.strip()]
            for line_num, raw_line in enumerate(raw_lines, start=1):
                normalized = normalize_whitespace(raw_line)
                is_unclear = any(token in normalized.lower() for token in UNCLEAR_TOKENS)
                line_confidence = min(confidence, 0.55) if is_unclear else confidence
                tier = classify_confidence(line_confidence)
                lines.append(
                    LineRecord(
                        text=normalized,
                        page=page_num,
                        line=line_num,
                        confidence=line_confidence,
                        tier=tier,
                        unclear_marker=is_unclear,
                    )
                )
        return lines

    def _detect_skipped_regions(self, text: str, confidence: float) -> list[dict]:
        skipped = []
        for page_num, page_text in enumerate(text.split("\f"), start=1):
            raw_lines = page_text.splitlines()
            blank_streak = 0
            streak_start = 0
            for i, raw in enumerate(raw_lines, start=1):
                if not raw.strip():
                    if blank_streak == 0:
                        streak_start = i
                    blank_streak += 1
                else:
                    if blank_streak >= 3:
                        skipped.append({
                            "page": page_num,
                            "line_start": streak_start,
                            "line_end": i - 1,
                            "reason": f"{blank_streak} consecutive blank lines — possible skipped content",
                        })
                    blank_streak = 0
            if blank_streak >= 3:
                skipped.append({
                    "page": page_num,
                    "line_start": streak_start,
                    "line_end": len(raw_lines),
                    "reason": f"{blank_streak} consecutive blank lines at end of page — possible skipped content",
                })
        return skipped

