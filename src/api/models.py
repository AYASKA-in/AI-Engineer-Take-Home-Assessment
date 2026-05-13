from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    case_id: str
    files_received: list[str]
    status: str = "accepted"


class ExtractionResponse(BaseModel):
    case_id: str
    documents: list[dict[str, Any]]
    metrics: dict[str, float]


class DraftRequest(BaseModel):
    case_id: str
    template_path: str = "data/templates_v1.json"


class DraftResponse(BaseModel):
    case_id: str
    memo_markdown: str
    metrics: dict[str, Any]
    section_grounding: list[dict[str, Any]]
    overall_grounding_status: str
    extraction_warnings: list[str]


class InspectResponse(BaseModel):
    case_id: str
    support_map: dict[str, list[dict[str, Any]]]
    section_grounding: list[dict[str, Any]]
    overall_grounding_status: str


class EditRequest(BaseModel):
    case_id: str
    original_draft: str
    edited_draft: str
    template_output_path: str = "data/templates_v2_learned.json"


class EditResponse(BaseModel):
    case_id: str
    patterns_detected: list[str]
    recommendations: list[str]
    updated_settings: dict[str, Any]


class GroundingScoreResponse(BaseModel):
    evidence_coverage: float
    citation_precision: float
    unsupported_claim_rate: float
    unclear_claim_rate: float
    avg_evidence_confidence: float
    sections_grounded: int
    sections_weak: int
    sections_insufficient: int
    overall_status: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
