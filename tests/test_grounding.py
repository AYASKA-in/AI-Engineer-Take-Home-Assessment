from __future__ import annotations

import unittest

from src.evaluation.grounding_metrics import (
    _extract_citations_from_memo,
    _validate_citation,
    compute_grounding_score,
)
from src.schema import (
    Chunk,
    DraftPackage,
    ExtractedDocument,
    GroundingStatus,
    LineRecord,
    RetrievalResult,
    SectionGrounding,
)


class TestCitationValidation(unittest.TestCase):
    def test_valid_citation_resolves(self) -> None:
        doc = ExtractedDocument(
            source_path="samples/case_files/case_a/complaint_scan.ocr.txt",
            doc_type="ocr",
            text="test",
            lines=[LineRecord(text="SUPREME COURT", page=1, line=1, confidence=0.7)],
            structured_fields={},
            average_confidence=0.7,
        )
        self.assertTrue(_validate_citation("complaint_scan.ocr.txt p1:1-1", [doc]))

    def test_invalid_citation_wrong_page(self) -> None:
        doc = ExtractedDocument(
            source_path="samples/case_files/case_a/complaint_scan.ocr.txt",
            doc_type="ocr",
            text="test",
            lines=[LineRecord(text="SUPREME COURT", page=1, line=1, confidence=0.7)],
            structured_fields={},
            average_confidence=0.7,
        )
        self.assertFalse(_validate_citation("complaint_scan.ocr.txt p5:1-1", [doc]))

    def test_invalid_citation_wrong_source(self) -> None:
        doc = ExtractedDocument(
            source_path="other_file.txt",
            doc_type="text",
            text="test",
            lines=[LineRecord(text="text", page=1, line=1, confidence=0.9)],
            structured_fields={},
            average_confidence=0.9,
        )
        self.assertFalse(_validate_citation("nonexistent.txt p1:1-1", [doc]))


class TestExtractCitations(unittest.TestCase):
    def test_extracts_citations_from_markdown(self) -> None:
        markdown = "- Some claim [complaint_scan.ocr.txt p1:1-4]\n- Another [site_notes.ocr.txt p2:5-8]"
        citations = _extract_citations_from_memo(markdown)
        self.assertEqual(len(citations), 2)
        self.assertIn("complaint_scan.ocr.txt p1:1-4", citations)

    def test_no_citations(self) -> None:
        citations = _extract_citations_from_memo("- No citations here")
        self.assertEqual(len(citations), 0)


class TestGroundingScore(unittest.TestCase):
    def test_compute_grounding_score_grounded(self) -> None:
        chunk = Chunk(
            chunk_id="test::1",
            source_path="test.txt",
            text="Plaintiff alleges breach of contract.",
            page_start=1,
            page_end=1,
            line_start=1,
            line_end=2,
            confidence=0.85,
        )
        result = RetrievalResult(
            chunk=chunk,
            score=0.5,
            lexical_score=0.3,
            semantic_score=0.4,
            rerank_score=0.1,
            matched_terms=["breach"],
        )
        draft = DraftPackage(
            memo_markdown="- Claim [test.txt p1:1-2]\n",
            section_evidence={"Summary": [result]},
            metrics={"substantive_lines": 1, "cited_lines": 1, "evidence_coverage": 1.0, "unsupported_claims": 0, "unclear_claims": 0},
            section_grounding=[
                SectionGrounding("Summary", GroundingStatus.GROUNDED, 1, 0.5, 0.85)
            ],
            overall_grounding_status=GroundingStatus.GROUNDED,
        )
        doc = ExtractedDocument(
            source_path="test.txt",
            doc_type="text",
            text="Plaintiff alleges breach of contract.",
            lines=[LineRecord(text="Plaintiff alleges breach of contract.", page=1, line=1, confidence=0.85)],
            structured_fields={},
            average_confidence=0.85,
        )
        score = compute_grounding_score(draft, [doc])
        self.assertEqual(score.overall_status, GroundingStatus.GROUNDED)
        self.assertGreater(score.evidence_coverage, 0)
        self.assertGreater(score.citation_precision, 0)

    def test_compute_grounding_score_insufficient(self) -> None:
        draft = DraftPackage(
            memo_markdown="- **INSUFFICIENT EVIDENCE** withheld\n",
            section_evidence={},
            metrics={"substantive_lines": 1, "cited_lines": 0, "evidence_coverage": 0.0, "unsupported_claims": 1, "unclear_claims": 0},
            section_grounding=[],
            overall_grounding_status=GroundingStatus.INSUFFICIENT_EVIDENCE,
        )
        score = compute_grounding_score(draft, [])
        self.assertGreater(score.unsupported_claim_rate, 0)


if __name__ == "__main__":
    unittest.main()
