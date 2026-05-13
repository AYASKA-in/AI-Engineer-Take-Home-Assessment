from __future__ import annotations

from pathlib import Path

from src.extractors.base_extractor import BaseExtractor
from src.schema import ExtractedDocument
from src.structured import extract_structured_fields


class OcrExtractor(BaseExtractor):
    def extract(self, path: str | Path) -> ExtractedDocument:
        file_path = Path(path)
        warnings: list[str] = []
        text = ""
        confidence = 0.68

        if file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8")
            confidence = 0.74
        else:
            sidecar_candidates = [
                Path(f"{file_path}.ocr.txt"),
                Path(f"{file_path}.txt"),
            ]
            for candidate in sidecar_candidates:
                if candidate.exists():
                    text = candidate.read_text(encoding="utf-8")
                    warnings.append(f"Used OCR sidecar text from {candidate.name}.")
                    confidence = 0.66
                    break

        if not text:
            try:
                import pytesseract  # type: ignore
                from PIL import Image  # type: ignore

                text = pytesseract.image_to_string(Image.open(file_path))
                confidence = 0.61
                warnings.append("OCR text extracted with pytesseract; confidence estimated heuristically.")
            except Exception as exc:
                raise RuntimeError(f"Unable to OCR {file_path}") from exc

        lines = self._build_lines(text, confidence=confidence)
        skipped = self._detect_skipped_regions(text, confidence=confidence)
        if any(token in text.lower() for token in ("[illegible]", "unclear", "??", "redacted")):
            warnings.append("Partially unclear OCR content detected.")
            confidence = min(confidence, 0.64)

        return ExtractedDocument(
            source_path=str(file_path),
            doc_type="ocr",
            text=text,
            lines=lines,
            structured_fields=extract_structured_fields(text),
            average_confidence=confidence,
            warnings=warnings,
            skipped_regions=skipped,
        )

