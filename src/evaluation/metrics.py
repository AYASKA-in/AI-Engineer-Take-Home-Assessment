from __future__ import annotations

from src.schema import DraftPackage, ExtractedDocument, classify_confidence


def extraction_metrics(documents: list[ExtractedDocument]) -> dict[str, float]:
    if not documents:
        return {"average_confidence": 0.0, "usable_chunk_ratio": 0.0, "structured_completeness": 0.0, "noisy_document_ratio": 0.0}

    average_confidence = sum(doc.average_confidence for doc in documents) / len(documents)
    usable_docs = sum(1 for doc in documents if doc.text.strip() and doc.average_confidence >= 0.6)
    noisy_docs = sum(1 for doc in documents if doc.average_confidence < 0.55)
    fields_present = 0
    fields_total = len(documents) * 4
    for doc in documents:
        counts = doc.structured_fields.get("field_counts", {})
        fields_present += sum(1 for key in ("dates", "parties", "sections", "amounts") if counts.get(key, 0) > 0)
    return {
        "average_confidence": round(average_confidence, 3),
        "usable_chunk_ratio": round(usable_docs / len(documents), 3),
        "structured_completeness": round(fields_present / fields_total, 3) if fields_total else 0.0,
        "noisy_document_ratio": round(noisy_docs / len(documents), 3),
    }


def draft_metrics(draft: DraftPackage) -> dict[str, float | int]:
    memo = draft.memo_markdown
    substantive_lines = draft.metrics["substantive_lines"]
    sections = memo.count("## ") - 1
    return {
        "section_count": sections,
        "substantive_lines": substantive_lines,
        "evidence_coverage": draft.metrics["evidence_coverage"],
        "unsupported_claims": draft.metrics["unsupported_claims"],
        "unclear_claims": draft.metrics.get("unclear_claims", 0),
        "overall_grounding": draft.overall_grounding_status.value,
    }

