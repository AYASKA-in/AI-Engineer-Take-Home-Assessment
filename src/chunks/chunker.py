from __future__ import annotations

from src.chunks.citation_anchors import group_lines
from src.schema import Chunk, ExtractedDocument
from src.utils import normalize_whitespace


def build_chunks(documents: list[ExtractedDocument], window: int = 4) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in documents:
        for index, block in enumerate(group_lines(doc.lines, window=window), start=1):
            text = normalize_whitespace(" ".join(line.text for line in block))
            if not text:
                continue
            avg_conf = sum(line.confidence for line in block) / len(block)
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.source_path}::chunk-{index}",
                    source_path=doc.source_path,
                    text=text,
                    page_start=block[0].page,
                    page_end=block[-1].page,
                    line_start=block[0].line,
                    line_end=block[-1].line,
                    confidence=avg_conf,
                    metadata={"doc_type": doc.doc_type},
                )
            )
    return chunks

