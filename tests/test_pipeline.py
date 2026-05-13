from __future__ import annotations

import unittest

from src.pipeline import generate_case_memo, grounding_payload, run_extraction
from src.schema import GroundingStatus


class PipelineGroundingTests(unittest.TestCase):
    def test_case_a_extraction_has_usable_outputs(self) -> None:
        documents = run_extraction("samples/case_files/case_a")
        self.assertGreaterEqual(len(documents), 3)
        self.assertTrue(any(doc.structured_fields["dates"] for doc in documents))
        self.assertTrue(any(doc.warnings for doc in documents))

    def test_grounding_payload_contains_support_map(self) -> None:
        documents, draft = generate_case_memo("samples/case_files/case_a")
        payload = grounding_payload("case_a", documents, draft)

        self.assertIn("support_map", payload)
        self.assertIn("Summary", payload["support_map"])
        self.assertIn("Matter overview", payload["support_map"])
        self.assertGreaterEqual(len(payload["support_map"]["Matter overview"]), 1)
        self.assertGreaterEqual(draft.metrics["substantive_lines"], 6)

    def test_draft_has_section_grounding(self) -> None:
        _, draft = generate_case_memo("samples/case_files/case_a")
        self.assertGreater(len(draft.section_grounding), 0)
        self.assertIn(draft.overall_grounding_status, (GroundingStatus.GROUNDED, GroundingStatus.WEAK_EVIDENCE))

    def test_grounding_payload_includes_confidence(self) -> None:
        documents, draft = generate_case_memo("samples/case_files/case_a")
        payload = grounding_payload("case_a", documents, draft)
        for section, results in payload["support_map"].items():
            for result in results:
                self.assertIn("confidence", result)


if __name__ == "__main__":
    unittest.main()

