from __future__ import annotations

import unittest

from src.schema import (
    ConfidenceTier,
    GroundingStatus,
    classify_confidence,
)


class TestConfidenceTier(unittest.TestCase):
    def test_high_confidence(self) -> None:
        self.assertEqual(classify_confidence(0.92), ConfidenceTier.HIGH)
        self.assertEqual(classify_confidence(0.85), ConfidenceTier.HIGH)

    def test_medium_confidence(self) -> None:
        self.assertEqual(classify_confidence(0.70), ConfidenceTier.MEDIUM)
        self.assertEqual(classify_confidence(0.65), ConfidenceTier.MEDIUM)

    def test_low_confidence(self) -> None:
        self.assertEqual(classify_confidence(0.50), ConfidenceTier.LOW)
        self.assertEqual(classify_confidence(0.45), ConfidenceTier.LOW)

    def test_unreadable_confidence(self) -> None:
        self.assertEqual(classify_confidence(0.30), ConfidenceTier.UNREADABLE)
        self.assertEqual(classify_confidence(0.0), ConfidenceTier.UNREADABLE)


if __name__ == "__main__":
    unittest.main()
