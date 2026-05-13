from __future__ import annotations

import unittest

from src.pipeline import generate_case_memo, run_extraction
from src.schema import GroundingStatus


class TestAbstainBehavior(unittest.TestCase):
    def test_case_d_signals_insufficient_evidence(self) -> None:
        documents, draft = generate_case_memo("samples/case_files/case_d")
        self.assertIn(
            draft.overall_grounding_status,
            (GroundingStatus.INSUFFICIENT_EVIDENCE, GroundingStatus.EXTRACTION_TOO_NOISY),
        )
        self.assertTrue(
            "INSUFFICIENT EVIDENCE" in draft.memo_markdown
            or "Weak evidence" in draft.memo_markdown
            or "Noisy source" in draft.memo_markdown
        )

    def test_case_a_does_not_abstain(self) -> None:
        documents, draft = generate_case_memo("samples/case_files/case_a")
        self.assertNotEqual(draft.overall_grounding_status, GroundingStatus.EXTRACTION_TOO_NOISY)

    def test_case_d_extraction_has_low_confidence(self) -> None:
        documents = run_extraction("samples/case_files/case_d")
        avg_conf = sum(d.average_confidence for d in documents) / len(documents)
        self.assertLess(avg_conf, 0.7)

    def test_case_d_documents_have_warnings(self) -> None:
        documents = run_extraction("samples/case_files/case_d")
        self.assertTrue(any(d.warnings for d in documents))

    def test_case_d_has_unclear_markers(self) -> None:
        documents = run_extraction("samples/case_files/case_d")
        has_unclear = any(line.unclear_marker for doc in documents for line in doc.lines)
        self.assertTrue(has_unclear)


class TestGroundingStatusOnNormalCases(unittest.TestCase):
    def test_case_a_grounded(self) -> None:
        _, draft = generate_case_memo("samples/case_files/case_a")
        self.assertIn(draft.overall_grounding_status, (GroundingStatus.GROUNDED, GroundingStatus.WEAK_EVIDENCE))

    def test_case_b_grounded(self) -> None:
        _, draft = generate_case_memo("samples/case_files/case_b")
        self.assertIn(
            draft.overall_grounding_status,
            (GroundingStatus.GROUNDED, GroundingStatus.WEAK_EVIDENCE, GroundingStatus.INSUFFICIENT_EVIDENCE),
        )

    def test_case_c_grounded(self) -> None:
        _, draft = generate_case_memo("samples/case_files/case_c")
        self.assertIn(draft.overall_grounding_status, (GroundingStatus.GROUNDED, GroundingStatus.WEAK_EVIDENCE))


class TestExtractionQualityNotes(unittest.TestCase):
    def test_case_a_has_extraction_warnings(self) -> None:
        documents, draft = generate_case_memo("samples/case_files/case_a")
        self.assertTrue(len(draft.extraction_warnings) > 0 or any(d.warnings for d in documents))


if __name__ == "__main__":
    unittest.main()
