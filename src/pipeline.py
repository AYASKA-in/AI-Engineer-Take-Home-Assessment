from __future__ import annotations

from pathlib import Path

from src.chunks.chunker import build_chunks
from src.edits.analyzer import analyze_edit
from src.edits.logger import append_edit_record
from src.edits.updater import apply_edit_learning
from src.edits.versioning import record_template_version
from src.evaluation.grounding_metrics import compute_grounding_score, grounding_score_to_dict
from src.evaluation.metrics import draft_metrics, extraction_metrics
from src.extractors.mixed_extractor import MixedExtractor
from src.retrieval.hybrid_search import HybridSearch
from src.schema import DraftPackage, ExtractedDocument
from src.templates.template_engine import TemplateEngine
from src.utils import dump_json


def list_case_files(input_dir: str | Path) -> list[Path]:
    return sorted(
        [
            path
            for path in Path(input_dir).iterdir()
            if path.is_file() and not path.name.startswith(".") and not path.name.endswith(".edited.md")
        ]
    )


def run_extraction(input_dir: str | Path) -> list[ExtractedDocument]:
    extractor = MixedExtractor()
    documents = []
    for path in list_case_files(input_dir):
        documents.append(extractor.extract(path))
    return documents


def extraction_payload(documents: list[ExtractedDocument]) -> dict[str, object]:
    return {
        "documents": [doc.to_dict() for doc in documents],
        "metrics": extraction_metrics(documents),
    }


def generate_case_memo(input_dir: str | Path, template_path: str | Path = "data/templates_v1.json") -> tuple[list[ExtractedDocument], DraftPackage]:
    documents = run_extraction(input_dir)
    chunks = build_chunks(documents)
    retriever = HybridSearch(chunks)
    engine = TemplateEngine(template_path=template_path)
    case_id = Path(input_dir).name
    draft = engine.generate(case_id=case_id, documents=documents, retriever=retriever)
    return documents, draft


def simulate_learning(
    case_dir: str | Path,
    original_draft: str,
    edited_draft: str,
    template_path: str | Path = "data/templates_v2_learned.json",
) -> dict[str, object]:
    case_id = Path(case_dir).name
    record = analyze_edit(case_id, original_draft, edited_draft)
    append_edit_record("data/edits.jsonl", record)
    updated = apply_edit_learning(record, template_path=template_path)
    record_template_version(template_path, case_id, record.patterns_detected)
    return updated


def save_extraction_output(path: str | Path, documents: list[ExtractedDocument]) -> None:
    dump_json(path, extraction_payload(documents))


def grounding_payload(case_id: str, documents: list[ExtractedDocument], draft: DraftPackage) -> dict[str, object]:
    return {
        "case_id": case_id,
        "documents": [doc.to_dict() for doc in documents],
        "draft": draft.to_dict(),
        "support_map": {
            section: [
                {
                    "citation": result.chunk.citation,
                    "text": result.chunk.text,
                    "score": round(result.score, 4),
                    "confidence": round(result.chunk.confidence, 3),
                }
                for result in results
            ]
            for section, results in draft.section_evidence.items()
        },
        "section_grounding": [sg.__dict__ for sg in draft.section_grounding],
        "overall_grounding_status": draft.overall_grounding_status.value,
    }


def save_grounding_output(path: str | Path, case_id: str, documents: list[ExtractedDocument], draft: DraftPackage) -> None:
    dump_json(path, grounding_payload(case_id, documents, draft))


def evaluation_bundle(documents: list[ExtractedDocument], draft: DraftPackage) -> dict[str, object]:
    grounding = compute_grounding_score(draft, documents)
    return {
        "extraction": extraction_metrics(documents),
        "draft": draft_metrics(draft),
        "grounding": grounding_score_to_dict(grounding),
    }
