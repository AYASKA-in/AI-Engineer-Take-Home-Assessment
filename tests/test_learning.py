from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.edits.analyzer import analyze_edit
from src.edits.updater import apply_edit_learning


class EditLearningTests(unittest.TestCase):
    def test_learning_updates_template_preferences(self) -> None:
        original = "- The plaintiff alleges breach of contract. [doc p1:1-2]"
        edited = (
            "- The plaintiff alleges breach of contract under Section 8 on October 5, 1984. "
            "[doc p1:1-2] [doc p1:1-2]"
        )
        record = analyze_edit("case_a", original, edited)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "template.json"
            updated = apply_edit_learning(record, template_path=template_path)
            persisted = json.loads(template_path.read_text(encoding="utf-8"))

        self.assertIn("added_section_specificity", record.patterns_detected)
        self.assertIn("increased_citation_density", record.patterns_detected)
        self.assertTrue(updated["require_section_citations"])
        self.assertGreaterEqual(updated["min_evidence_per_section"], 3)
        self.assertEqual(persisted["min_evidence_per_section"], updated["min_evidence_per_section"])

    def test_section_reordering_updates_template(self) -> None:
        original = "## Matter overview\n## Key parties\n## Timeline\n- Claim [doc p1:1-2]"
        edited = "## Key parties\n## Matter overview\n## Timeline\n- Claim [doc p1:1-2]"
        record = analyze_edit("case_a", original, edited)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "template.json"
            updated = apply_edit_learning(record, template_path=template_path)

        self.assertIn("reordered_sections", record.patterns_detected)
        self.assertEqual(updated["section_order"], ["Key parties", "Matter overview", "Timeline"])

    def test_formal_phrasing_updates_template(self) -> None:
        original = "- The plaintiff appears to have a case. [doc p1:1-2]"
        edited = "- The plaintiff alleges breach and furthermore contends damages are owed pursuant to the agreement. [doc p1:1-2]"
        record = analyze_edit("case_a", original, edited)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "template.json"
            updated = apply_edit_learning(record, template_path=template_path)

        self.assertIn("formalized_phrasing", record.patterns_detected)
        self.assertEqual(updated["phrasing_style"], "formal")

    def test_missing_field_updates_retrieval_boost(self) -> None:
        original = "- The plaintiff alleges breach. [doc p1:1-2]"
        edited = "- The plaintiff alleges breach of contract under Section 8. [doc p1:1-2]"
        record = analyze_edit("case_a", original, edited)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "template.json"
            updated = apply_edit_learning(record, template_path=template_path)

        self.assertIn("missing_field_section", record.patterns_detected)
        self.assertIn("section", updated["retrieval_boost_terms"])


if __name__ == "__main__":
    unittest.main()

