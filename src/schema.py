from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNREADABLE = "UNREADABLE"


class GroundingStatus(str, Enum):
    GROUNDED = "GROUNDED"
    WEAK_EVIDENCE = "WEAK_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    EXTRACTION_TOO_NOISY = "EXTRACTION_TOO_NOISY"


def classify_confidence(confidence: float) -> ConfidenceTier:
    if confidence >= 0.85:
        return ConfidenceTier.HIGH
    if confidence >= 0.65:
        return ConfidenceTier.MEDIUM
    if confidence >= 0.45:
        return ConfidenceTier.LOW
    return ConfidenceTier.UNREADABLE


@dataclass
class LineRecord:
    text: str
    page: int
    line: int
    confidence: float
    tier: ConfidenceTier = ConfidenceTier.HIGH
    unclear_marker: bool = False


@dataclass
class ExtractedDocument:
    source_path: str
    doc_type: str
    text: str
    lines: list[LineRecord]
    structured_fields: dict[str, Any]
    average_confidence: float
    warnings: list[str] = field(default_factory=list)
    skipped_regions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def overall_tier(self) -> ConfidenceTier:
        return classify_confidence(self.average_confidence)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["overall_tier"] = self.overall_tier.value
        return payload


@dataclass
class Chunk:
    chunk_id: str
    source_path: str
    text: str
    page_start: int
    page_end: int
    line_start: int
    line_end: int
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        name = self.source_path.replace("\\", "/").split("/")[-1]
        if self.page_start == self.page_end:
            return f"{name} p{self.page_start}:{self.line_start}-{self.line_end}"
        return (
            f"{name} p{self.page_start}:{self.line_start}-"
            f"p{self.page_end}:{self.line_end}"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["citation"] = self.citation
        return payload


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    lexical_score: float
    semantic_score: float
    rerank_score: float
    matched_terms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": round(self.score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "rerank_score": round(self.rerank_score, 4),
            "matched_terms": self.matched_terms,
        }


@dataclass
class SectionGrounding:
    section_name: str
    status: GroundingStatus
    evidence_count: int
    top_score: float
    avg_confidence: float
    reason: str = ""

@dataclass
class DraftPackage:
    memo_markdown: str
    section_evidence: dict[str, list[RetrievalResult]]
    metrics: dict[str, Any]
    section_grounding: list[SectionGrounding] = field(default_factory=list)
    overall_grounding_status: GroundingStatus = GroundingStatus.GROUNDED
    extraction_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memo_markdown": self.memo_markdown,
            "section_evidence": {
                section: [result.to_dict() for result in results]
                for section, results in self.section_evidence.items()
            },
            "metrics": self.metrics,
            "section_grounding": [asdict(sg) for sg in self.section_grounding],
            "overall_grounding_status": self.overall_grounding_status.value,
            "extraction_warnings": self.extraction_warnings,
        }


@dataclass
class EditRecord:
    case_id: str
    original_draft: str
    edited_draft: str
    patterns_detected: list[str]
    recommendations: list[str]
    metadata: dict[str, Any]


DEFAULT_TEMPLATE_SETTINGS = {
    "prefer_formal_dates": True,
    "require_section_citations": True,
    "claim_detail_expansion": "medium",
    "min_evidence_per_section": 1,
    "include_open_questions": True,
    "min_retrieval_score": 0.10,
    "min_extraction_confidence": 0.45,
    "abstain_on_insufficient_evidence": True,
    "section_order": ["Matter overview", "Key parties", "Timeline", "Allegations and obligations", "Open questions"],
    "phrasing_style": "standard",
    "retrieval_boost_terms": [],
}
