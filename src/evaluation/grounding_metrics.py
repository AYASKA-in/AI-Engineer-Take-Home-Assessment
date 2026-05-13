from __future__ import annotations

import re
from dataclasses import dataclass

from src.schema import DraftPackage, ExtractedDocument, GroundingStatus, SectionGrounding


@dataclass
class GroundingScore:
    evidence_coverage: float
    citation_precision: float
    unsupported_claim_rate: float
    unclear_claim_rate: float
    avg_evidence_confidence: float
    sections_grounded: int
    sections_weak: int
    sections_insufficient: int
    overall_status: GroundingStatus


def _validate_citation(citation: str, documents: list[ExtractedDocument]) -> bool:
    match = re.match(r"(.+) p(\d+):(\d+)-(\d+)", citation)
    if not match:
        return False
    source_name = match.group(1).strip()
    page = int(match.group(2))
    line_start = int(match.group(3))
    line_end = int(match.group(4))

    for doc in documents:
        if source_name in doc.source_path.replace("\\", "/"):
            matching_lines = [
                line for line in doc.lines
                if line.page == page and line_start <= line.line <= line_end
            ]
            if matching_lines:
                return True
    return False


def _extract_citations_from_memo(markdown: str) -> list[str]:
    citations = []
    for match in re.finditer(r"\[([^\]]+ p\d+:\d+-\d+)\]", markdown):
        citations.append(match.group(1))
    return citations


def compute_grounding_score(
    draft: DraftPackage,
    documents: list[ExtractedDocument],
) -> GroundingScore:
    memo = draft.memo_markdown
    metrics = draft.metrics

    citations = _extract_citations_from_memo(memo)
    valid_citations = sum(1 for cite in citations if _validate_citation(cite, documents))
    citation_precision = valid_citations / len(citations) if citations else 0.0

    substantive = metrics.get("substantive_lines", 0)
    cited = metrics.get("cited_lines", 0)
    unsupported = metrics.get("unsupported_claims", 0)
    unclear = metrics.get("unclear_claims", 0)

    evidence_coverage = cited / substantive if substantive else 0.0
    unsupported_rate = unsupported / substantive if substantive else 0.0
    unclear_rate = unclear / substantive if substantive else 0.0

    all_evidence_chunks: list[float] = []
    for results in draft.section_evidence.values():
        for result in results:
            all_evidence_chunks.append(result.chunk.confidence)
    avg_conf = sum(all_evidence_chunks) / len(all_evidence_chunks) if all_evidence_chunks else 0.0

    sections_grounded = sum(
        1 for sg in draft.section_grounding if sg.status == GroundingStatus.GROUNDED
    )
    sections_weak = sum(
        1 for sg in draft.section_grounding
        if sg.status in (GroundingStatus.WEAK_EVIDENCE, GroundingStatus.EXTRACTION_TOO_NOISY)
    )
    sections_insufficient = sum(
        1 for sg in draft.section_grounding if sg.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    )

    return GroundingScore(
        evidence_coverage=round(evidence_coverage, 3),
        citation_precision=round(citation_precision, 3),
        unsupported_claim_rate=round(unsupported_rate, 3),
        unclear_claim_rate=round(unclear_rate, 3),
        avg_evidence_confidence=round(avg_conf, 3),
        sections_grounded=sections_grounded,
        sections_weak=sections_weak,
        sections_insufficient=sections_insufficient,
        overall_status=draft.overall_grounding_status,
    )


def grounding_score_to_dict(score: GroundingScore) -> dict:
    return {
        "evidence_coverage": score.evidence_coverage,
        "citation_precision": score.citation_precision,
        "unsupported_claim_rate": score.unsupported_claim_rate,
        "unclear_claim_rate": score.unclear_claim_rate,
        "avg_evidence_confidence": score.avg_evidence_confidence,
        "sections_grounded": score.sections_grounded,
        "sections_weak": score.sections_weak,
        "sections_insufficient": score.sections_insufficient,
        "overall_status": score.overall_status.value,
    }
