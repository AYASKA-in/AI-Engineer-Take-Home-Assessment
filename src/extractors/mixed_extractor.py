from __future__ import annotations

import logging
from pathlib import Path

from src.extractors.ocr_extractor import OcrExtractor
from src.extractors.pdf_extractor import PdfExtractor
from src.router import DocumentRouter
from src.schema import ConfidenceTier, ExtractedDocument, LineRecord, classify_confidence
from src.structured import extract_structured_fields

logger = logging.getLogger(__name__)


class MixedExtractor:
    def __init__(self) -> None:
        self.router = DocumentRouter()
        self.pdf_extractor = PdfExtractor()
        self.ocr_extractor = OcrExtractor()

    def extract(self, path: str | Path) -> ExtractedDocument:
        route = self.router.route(path)
        file_path = Path(path)
        warnings: list[str] = []

        if route == "pdf":
            try:
                return self.pdf_extractor.extract(file_path)
            except Exception as exc:
                logger.warning("PDF extraction failed for %s: %s — falling back to OCR sidecar", file_path, exc)
                warnings.append(f"PDF extraction failed ({exc}); attempted OCR fallback.")
                try:
                    return self.ocr_extractor.extract(file_path)
                except Exception as fallback_exc:
                    logger.error("OCR fallback also failed for %s: %s", file_path, fallback_exc)
                    return self._empty_document(file_path, warnings + [f"OCR fallback also failed ({fallback_exc})."])

        if route == "ocr":
            try:
                return self.ocr_extractor.extract(file_path)
            except Exception as exc:
                logger.error("OCR extraction failed for %s: %s", file_path, exc)
                return self._empty_document(file_path, [f"OCR extraction failed ({exc})."])

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Text read failed for %s: %s", file_path, exc)
            return self._empty_document(file_path, [f"Could not read file ({exc})."])

        lines = self.ocr_extractor._build_lines(text, confidence=0.96)
        skipped = self.ocr_extractor._detect_skipped_regions(text, confidence=0.96)
        if "redacted" in text.lower():
            warnings.append("Redacted content detected.")
        return ExtractedDocument(
            source_path=str(file_path),
            doc_type="text",
            text=text,
            lines=lines,
            structured_fields=extract_structured_fields(text),
            average_confidence=0.96,
            warnings=warnings,
            skipped_regions=skipped,
        )

    def _empty_document(self, file_path: Path, warnings: list[str]) -> ExtractedDocument:
        return ExtractedDocument(
            source_path=str(file_path),
            doc_type="unreadable",
            text="",
            lines=[],
            structured_fields={"dates": [], "parties": [], "sections": [], "amounts": [], "allegations": [], "obligations": [], "field_counts": {}},
            average_confidence=0.0,
            warnings=warnings,
            skipped_regions=[{"page": 1, "line_start": 1, "line_end": 1, "reason": "Entire document unreadable"}],
        )

