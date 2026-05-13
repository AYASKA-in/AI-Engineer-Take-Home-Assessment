from __future__ import annotations

import unittest

from src.structured import extract_structured_fields


class StructuredExtractionTests(unittest.TestCase):
    def test_extracts_core_fields_from_legal_style_text(self) -> None:
        text = (
            "Plaintiff: Hudson Valley Development LLC\n"
            "Defendant: Mercer Construction Group, Inc.\n"
            "The parties signed the agreement on October 5, 1984.\n"
            "Section 8 required weekly site reports.\n"
            "Invoice sought payment of $185,000.\n"
        )

        fields = extract_structured_fields(text)

        self.assertIn("Hudson Valley Development LLC", fields["parties"])
        self.assertIn("October 5, 1984", fields["dates"])
        self.assertIn("Section 8", fields["sections"])
        self.assertIn("$185,000", fields["amounts"])


if __name__ == "__main__":
    unittest.main()

