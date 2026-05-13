from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException

from src.api.models import (
    DraftRequest,
    DraftResponse,
    EditRequest,
    EditResponse,
    ExtractionResponse,
    GroundingScoreResponse,
    HealthResponse,
    InspectResponse,
    UploadResponse,
)
from src.evaluation.grounding_metrics import compute_grounding_score, grounding_score_to_dict
from src.pipeline import (
    generate_case_memo,
    grounding_payload,
    run_extraction,
    simulate_learning,
)

app = FastAPI(
    title="Pearson Specter Litt — Grounded Drafting API",
    description="Ingest messy legal documents, extract, retrieve, draft grounded memos, and learn from edits.",
    version="1.0.0",
)

_upload_dir = Path(tempfile.mkdtemp(prefix="psl_uploads_"))


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse()


@app.post("/upload", response_model=UploadResponse)
async def upload_files(case_id: str, files: list[UploadFile] = File(...)) -> UploadResponse:
    case_dir = _upload_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for upload in files:
        dest = case_dir / upload.filename
        with dest.open("wb") as f:
            content = await upload.read()
            f.write(content)
        saved.append(upload.filename)
    return UploadResponse(case_id=case_id, files_received=saved)


@app.get("/extract/{case_id}", response_model=ExtractionResponse)
def extract_documents(case_id: str) -> ExtractionResponse:
    case_dir = _upload_dir / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found. Upload files first.")
    documents = run_extraction(case_dir)
    from src.evaluation.metrics import extraction_metrics
    return ExtractionResponse(
        case_id=case_id,
        documents=[doc.to_dict() for doc in documents],
        metrics=extraction_metrics(documents),
    )


@app.post("/draft", response_model=DraftResponse)
def generate_draft(request: DraftRequest) -> DraftResponse:
    case_dir = _upload_dir / request.case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"Case '{request.case_id}' not found. Upload files first.")
    documents, draft = generate_case_memo(case_dir, template_path=request.template_path)
    return DraftResponse(
        case_id=request.case_id,
        memo_markdown=draft.memo_markdown,
        metrics=draft.metrics,
        section_grounding=[sg.__dict__ for sg in draft.section_grounding],
        overall_grounding_status=draft.overall_grounding_status.value,
        extraction_warnings=draft.extraction_warnings,
    )


@app.get("/inspect/{case_id}", response_model=InspectResponse)
def inspect_grounding(case_id: str, template_path: str = "data/templates_v1.json") -> InspectResponse:
    case_dir = _upload_dir / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found. Upload files first.")
    documents, draft = generate_case_memo(case_dir, template_path=template_path)
    payload = grounding_payload(case_id, documents, draft)
    return InspectResponse(
        case_id=case_id,
        support_map=payload["support_map"],
        section_grounding=payload["section_grounding"],
        overall_grounding_status=payload["overall_grounding_status"],
    )


@app.get("/grounding-score/{case_id}", response_model=GroundingScoreResponse)
def get_grounding_score(case_id: str, template_path: str = "data/templates_v1.json") -> GroundingScoreResponse:
    case_dir = _upload_dir / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found. Upload files first.")
    documents, draft = generate_case_memo(case_dir, template_path=template_path)
    score = compute_grounding_score(draft, documents)
    return GroundingScoreResponse(
        evidence_coverage=score.evidence_coverage,
        citation_precision=score.citation_precision,
        unsupported_claim_rate=score.unsupported_claim_rate,
        unclear_claim_rate=score.unclear_claim_rate,
        avg_evidence_confidence=score.avg_evidence_confidence,
        sections_grounded=score.sections_grounded,
        sections_weak=score.sections_weak,
        sections_insufficient=score.sections_insufficient,
        overall_status=score.overall_status.value,
    )


@app.post("/edit", response_model=EditResponse)
def submit_edit(request: EditRequest) -> EditResponse:
    from src.edits.analyzer import analyze_edit
    record = analyze_edit(request.case_id, request.original_draft, request.edited_draft)
    updated = simulate_learning(
        request.case_id,
        request.original_draft,
        request.edited_draft,
        template_path=request.template_output_path,
    )
    return EditResponse(
        case_id=request.case_id,
        patterns_detected=record.patterns_detected,
        recommendations=record.recommendations,
        updated_settings=updated,
    )
