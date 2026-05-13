from __future__ import annotations

from pathlib import Path


class DocumentRouter:
    """Simple routing heuristic for clean, OCR-style, and mixed inputs."""

    OCR_HINTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

    def route(self, path: str | Path) -> str:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()

        if name.endswith(".ocr.txt"):
            return "ocr"
        if suffix in self.OCR_HINTS:
            return "ocr"
        if suffix == ".pdf":
            return "pdf"
        if suffix in {".txt", ".md"} and any(
            token in name for token in ("scan", "handwritten", "note", "ocr")
        ):
            return "ocr"
        return "text"

