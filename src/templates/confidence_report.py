from __future__ import annotations

from src.templates.validators import memo_lines_with_citations, unclear_lines, unsupported_lines


def build_confidence_report(markdown: str) -> dict[str, float | int]:
    substantive, cited = memo_lines_with_citations(markdown)
    unsupported = len(unsupported_lines(markdown))
    unclear = len(unclear_lines(markdown))
    coverage = cited / substantive if substantive else 0.0
    return {
        "substantive_lines": substantive,
        "cited_lines": cited,
        "evidence_coverage": round(coverage, 3),
        "unsupported_claims": unsupported,
        "unclear_claims": unclear,
    }

