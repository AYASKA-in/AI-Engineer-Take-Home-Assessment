from __future__ import annotations

import unittest

from src.edits.analyzer import (
    _detect_missing_fields,
    _detect_phrasing_shift,
    _detect_retrieval_boost_candidates,
    _detect_section_reordering,
    analyze_edit,
)


class TestSectionReordering(unittest.TestCase):
    def test_detects_reorder(self) -> None:
        original = "## Matter overview\n## Key parties\n## Timeline"
        edited = "## Key parties\n## Matter overview\n## Timeline"
        reordered, new_order = _detect_section_reordering(original, edited)
        self.assertTrue(reordered)
        self.assertEqual(new_order, ["Key parties", "Matter overview", "Timeline"])

    def test_no_reorder(self) -> None:
        original = "## Matter overview\n## Key parties"
        edited = "## Matter overview\n## Key parties"
        reordered, _ = _detect_section_reordering(original, edited)
        self.assertFalse(reordered)


class TestPhrasingShift(unittest.TestCase):
    def test_formal_shift(self) -> None:
        original = "The plaintiff appears to have a case."
        edited = "The plaintiff alleges breach and furthermore contends that damages are owed pursuant to the agreement."
        result = _detect_phrasing_shift(original, edited)
        self.assertEqual(result, "formal")

    def test_no_shift(self) -> None:
        original = "The plaintiff alleges breach of contract."
        edited = "The plaintiff alleges breach of contract under Section 8."
        result = _detect_phrasing_shift(original, edited)
        self.assertIsNone(result)


class TestMissingFields(unittest.TestCase):
    def test_detects_added_section(self) -> None:
        original = "The plaintiff alleges breach of contract."
        edited = "The plaintiff alleges breach of contract under Section 8."
        missing = _detect_missing_fields(original, edited)
        self.assertIn("section", missing)

    def test_detects_added_amount(self) -> None:
        original = "Invoice sought payment."
        edited = "Invoice sought payment of $185,000."
        missing = _detect_missing_fields(original, edited)
        self.assertIn("amount", missing)

    def test_no_missing_fields(self) -> None:
        original = "Section 8 required reports. Payment of $185,000."
        edited = "Section 8 required reports. Payment of $185,000 was due."
        missing = _detect_missing_fields(original, edited)
        self.assertEqual(len(missing), 0)


class TestRetrievalBoostCandidates(unittest.TestCase):
    def test_detects_section_boost(self) -> None:
        original = "- The plaintiff alleges breach."
        edited = "- The plaintiff alleges breach under Section 8."
        candidates = _detect_retrieval_boost_candidates(original, edited)
        self.assertTrue(any("section 8" in c.lower() for c in candidates))

    def test_detects_amount_boost(self) -> None:
        original = "- Invoice sought payment."
        edited = "- Invoice sought payment of $185,000."
        candidates = _detect_retrieval_boost_candidates(original, edited)
        self.assertIn("$185,000", candidates)


class TestFullAnalysis(unittest.TestCase):
    def test_comprehensive_edit(self) -> None:
        original = (
            "# First-Pass Internal Memo: case_a\n\n"
            "## Matter overview\n"
            "## Key parties\n"
            "- The plaintiff alleges breach of contract. [doc p1:1-2]\n"
        )
        edited = (
            "# First-Pass Internal Memo: case_a\n\n"
            "## Key parties\n"
            "## Matter overview\n"
            "- The plaintiff alleges breach of contract under Section 8 on October 5, 1984. "
            "The plaintiff furthermore contends that damages of $185,000 are owed pursuant to the agreement. "
            "[doc p1:1-2] [doc p1:3-4]\n"
        )
        record = analyze_edit("case_a", original, edited)
        self.assertIn("added_section_specificity", record.patterns_detected)
        self.assertIn("increased_citation_density", record.patterns_detected)
        self.assertIn("formalized_dates", record.patterns_detected)
        self.assertIn("expanded_claim_descriptions", record.patterns_detected)
        self.assertIn("reordered_sections", record.patterns_detected)
        self.assertIn("formalized_phrasing", record.patterns_detected)
        self.assertIn("missing_field_section", record.patterns_detected)
        self.assertIn("missing_field_amount", record.patterns_detected)
        self.assertIn("retrieval_boost_candidates", record.patterns_detected)
        self.assertIsNotNone(record.metadata.get("section_order"))
        self.assertEqual(record.metadata["phrasing_preference"], "formal")


if __name__ == "__main__":
    unittest.main()
