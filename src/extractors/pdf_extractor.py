from __future__ import annotations

from pathlib import Path

from src.extractors.base_extractor import BaseExtractor
from src.schema import ExtractedDocument
from src.structured import extract_structured_fields


class PdfExtractor(BaseExtractor):
    def extract(self, path: str | Path) -> ExtractedDocument:
        file_path = Path(path)
        warnings: list[str] = []
        text = ""

        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            text = "\f".join(pages)
        except Exception as exc:
            sidecar = Path(f"{file_path}.txt")
            if sidecar.exists():
                text = sidecar.read_text(encoding="utf-8")
                warnings.append(f"PDF parser unavailable or failed; used sidecar text ({exc}).")
            else:
                raise RuntimeError(f"Unable to extract PDF text from {file_path}") from exc

        lines = self._build_lines(text, confidence=0.92)
        skipped = self._detect_skipped_regions(text, confidence=0.92)
        return ExtractedDocument(
            source_path=str(file_path),
            doc_type="pdf",
            text=text,
            lines=lines,
            structured_fields=extract_structured_fields(text),
            average_confidence=0.92,
            warnings=warnings,
            skipped_regions=skipped,
        )

