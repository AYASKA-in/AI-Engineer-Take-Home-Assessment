# Architecture Overview

This document describes the system's data flow, component responsibilities, key data structures, and design rationale.

---

## Core Data Flow

```
Input files
    │
    ▼
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Router       │────▶│  Extractors      │────▶│  Chunker          │
│  (classify)   │     │  (text + fields  │     │  (page:line      │
│               │     │   + confidence)  │     │   anchors)       │
└──────────────┘     └──────────────────┘     └──────────────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  Hybrid Search    │
                                             │  (lexical + TF-IDF│
                                             │   + reranking)    │
                                             └──────────────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  Grounding Check  │
                                             │  (per-section)    │
                                             └──────────────────┘
                                              │    │    │    │
                                    GROUNDED  │    │    │    │  INSUFFICIENT
                                              │    │    │    │  EVIDENCE
                                              ▼    ▼    ▼    ▼
                                        ┌─────────────────────────┐
                                        │  Template Engine        │
                                        │  (draft or abstain)     │
                                        └─────────────────────────┘
                                                      │
                                                      ▼
                                        ┌─────────────────────────┐
                                        │  Operator Edit          │
                                        │  (capture + analyze    │
                                        │   + update template)   │
                                        └─────────────────────────┘
                                                      │
                                                      ▼
                                        ┌─────────────────────────┐
                                        │  Versioned Template     │
                                        │  (feeds back into       │
                                        │   next draft cycle)    │
                                        └─────────────────────────┘
```

---

## Component Responsibilities

### 1. Router (`src/router.py`)

Classifies each input file by type:
- **text**: `.txt` files without OCR indicators → `TextExtractor`
- **pdf**: `.pdf` files → `PdfExtractor`
- **ocr**: files with `.ocr.txt` extension or OCR indicators → `OcrExtractor`

The router is a simple rule-based classifier. It does not attempt content sniffing — the classification is based on filename patterns, which is sufficient for the legal document domain where naming conventions are consistent.

### 2. Extractors (`src/extractors/`)

Each extractor converts a raw file into an `ExtractedDocument` containing:
- `source_path` — original filename
- `doc_type` — "text", "pdf", or "ocr"
- `lines` — list of `LineRecord` objects (text, page, line number, confidence, tier, unclear marker)
- `average_confidence` — mean confidence across all lines
- `structured_fields` — extracted dates, parties, sections, amounts, allegations, obligations
- `warnings` — e.g. "Partially unclear OCR content detected"
- `skipped_regions` — ranges of consecutive blank lines

**BaseExtractor** (`base_extractor.py`) provides shared logic:
- `classify_confidence_tier()` — maps a confidence float to HIGH/MEDIUM/LOW/UNREADABLE
- `detect_unclear_tokens()` — flags lines containing `[illegible]`, `???`, `[unreadable]`, `redacted`, `unclear`
- `detect_skipped_regions()` — finds runs of blank lines

**PdfExtractor** (`pdf_extractor.py`): Uses `pypdf` to extract text from real PDFs. Falls back gracefully if the library is unavailable or the PDF is corrupted.

**OcrExtractor** (`ocr_extractor.py`): Reads `.ocr.txt` sidecar files (or uses `pytesseract` for real image OCR). Applies unclear-token detection and confidence reduction for OCR-style content.

**MixedExtractor** (`mixed_extractor.py`): The main entry point. Routes each file, applies fallback chains (PDF → OCR → empty doc with warnings), and aggregates results. Includes retry logic with logging.

### 3. Chunker (`src/chunks/`)

**chunker.py**: Groups extracted lines into `Chunk` objects. Each chunk:
- Contains 1–6 consecutive lines from the same source
- Carries `page:line` provenance (e.g. `p1:5-8`)
- Has an average confidence score across its lines
- Gets a stable `chunk_id` like `complaint_scan.ocr.txt::chunk-1`

**embeddings.py**: Builds a lightweight TF-IDF index over all chunks. No external embedding model required — uses term frequency × inverse document frequency for semantic similarity.

### 4. Retrieval (`src/retrieval/`)

**hybrid_search.py**: The `HybridSearch` class performs retrieval over chunks for a given query:

```
score = 0.55 × lexical_overlap + 0.35 × tfidf_cosine + rerank_bonus + 0.10 × chunk_confidence
```

- **Lexical overlap**: fraction of query terms found in the chunk
- **TF-IDF cosine**: lightweight semantic similarity
- **Rerank bonus**: additive bonuses for section refs, entities, digits, date patterns
- **Confidence signal**: chunk quality as a tiebreaker

**top_k_rerank.py**: Provides structured reranking bonuses:
- Section reference match (+0.08)
- Named entity match (+0.07)
- Digit co-occurrence (+0.05)
- Date-pattern match (+0.06) — when query contains date-related terms and chunk contains date patterns
- Low-confidence penalty (-0.05) for chunks below 0.6 confidence

**provenance.py**: Generates citation strings from chunk metadata, e.g. `[complaint_scan.ocr.txt p1:5-8]`.

### 5. Template Engine (`src/templates/`)

**template_engine.py**: The `TemplateEngine` class generates the first-pass internal memo:

1. **Section queries**: For each memo section, a targeted query is constructed using the section name + structured fields + learned retrieval boost terms
2. **Evidence retrieval**: `HybridSearch` returns scored chunks for each section query
3. **Grounding classification**: Each section's evidence is classified as GROUNDED / WEAK_EVIDENCE / INSUFFICIENT_EVIDENCE / EXTRACTION_TOO_NOISY
4. **Draft or abstain**: Based on the grounding status:
   - GROUNDED → full draft with inline citations
   - WEAK_EVIDENCE → draft with caution note
   - INSUFFICIENT_EVIDENCE → draft withheld, `**INSUFFICIENT EVIDENCE**` marker
   - EXTRACTION_TOO_NOISY → draft withheld, `⚠ EXTRACTION TOO NOISY` marker
5. **Assembly**: Sections are ordered according to template `section_order` (which can be learned from edits)

**validators.py**: Detects unsupported claims (substantive lines without citations) and unclear claims (lines with `[UNCLEAR]` or `LOW-CONF` markers).

**confidence_report.py**: Produces a confidence summary including counts of unclear and unsupported claims.

### 6. Edit Learning (`src/edits/`)

**logger.py**: Logs every edit to `data/edits.jsonl` with:
- `case_id`, `original_draft`, `edited_draft`
- `patterns_detected`, `recommendations`
- `metadata` (timestamp, etc.)

**analyzer.py**: The `analyze_edit()` function compares original and edited drafts to detect 9 pattern types:

| Pattern | Detection Method |
| --- | --- |
| `added_section_specificity` | Diff adds "Section X" references |
| `increased_citation_density` | Diff adds more `[source pX:Y-Z]` citations |
| `formalized_dates` | Diff replaces numeric dates with formal style |
| `expanded_claim_descriptions` | Diff adds descriptive text to terse claims |
| `reordered_sections` | Section headers appear in different order |
| `formalized_phrasing` | Diff shifts toward formal legal language |
| `informal_phrasing` | Diff shifts toward informal language |
| `missing_field_{X}` | Diff adds references to field X not in original |
| `retrieval_boost_candidates` | Specific terms extracted from added content |

**updater.py**: Applies detected patterns to template settings:
- `section_order` ← from reorder detection
- `phrasing_style` ← from phrasing shift detection
- `min_evidence_per_section` ← from citation density
- `retrieval_boost_terms` ← from missing field and boost candidate detection
- `claim_detail_expansion` ← from expanded claim detection
- `require_section_citations` ← from section specificity detection

**versioning.py**: Records every template update to `data/template_history.jsonl` with:
- `timestamp`
- `triggered_patterns` — which patterns caused this update
- `settings_snapshot` — full template settings after the update

### 7. Evaluation (`src/evaluation/`)

**metrics.py**: Computes extraction metrics (average confidence, structured completeness, usable chunk ratio, noisy document ratio) and draft metrics (substantive lines, evidence coverage, unsupported claims, unclear claims, overall grounding).

**grounding_metrics.py**: The `compute_grounding_score()` function:
- Extracts citations from the draft markdown
- Validates each citation against actual source lines (not just pattern matching)
- Computes: evidence_coverage, citation_precision, unsupported_claim_rate, unclear_claim_rate, avg_evidence_confidence
- Counts sections by grounding status (grounded / weak / insufficient)
- Determines overall grounding status

### 8. API (`src/api/`)

**models.py**: Pydantic request/response schemas for all endpoints.

**endpoints.py**: FastAPI route handlers. The API maintains an in-memory store of uploaded documents and generated drafts, keyed by `case_id`. This allows the full workflow (upload → extract → draft → inspect → grounding score → edit) to be exercised via HTTP.

---

## Key Data Structures

### `LineRecord` (`src/schema.py`)
```python
@dataclass
class LineRecord:
    text: str
    page: int
    line_number: int
    confidence: float
    tier: ConfidenceTier       # HIGH / MEDIUM / LOW / UNREADABLE
    unclear_marker: bool       # True if line contains unclear tokens
```

### `ExtractedDocument` (`src/schema.py`)
```python
@dataclass
class ExtractedDocument:
    source_path: str
    doc_type: str              # "text" / "pdf" / "ocr"
    lines: list[LineRecord]
    average_confidence: float
    structured_fields: dict    # dates, parties, sections, amounts, etc.
    warnings: list[str]
    skipped_regions: list[tuple[int, int]]
```

### `DraftPackage` (`src/schema.py`)
```python
@dataclass
class DraftPackage:
    case_id: str
    memo_markdown: str
    evidence: dict[str, list]  # section → evidence chunks
    metrics: dict
    section_grounding: list[SectionGrounding]
    overall_grounding_status: GroundingStatus
    extraction_warnings: list[str]
```

### `SectionGrounding` (`src/schema.py`)
```python
@dataclass
class SectionGrounding:
    section_name: str
    status: GroundingStatus    # GROUNDED / WEAK_EVIDENCE / INSUFFICIENT_EVIDENCE / EXTRACTION_TOO_NOISY
    evidence_count: int
    top_score: float
    avg_confidence: float
    reason: str                # Human-readable explanation
```

---

## Design Choices

| Choice | Rationale | Tradeoff |
| --- | --- | --- |
| Deterministic drafting (no LLM) | Grounding is verifiable; no hallucination risk; runs offline | Less expressive writing |
| Rule-based field extraction | Transparent, auditable, no training data needed | Weaker recall on unusual formats |
| In-memory TF-IDF retrieval | Zero infra, instant setup for reviewers | Not scalable to massive corpora |
| Per-section grounding check | Prevents section-level hallucination | Some sections may be withheld |
| Strict abstain behavior | Trustworthiness over completeness | Empty sections on weak evidence |
| Fallback chains (PDF → OCR → empty) | Pipeline never crashes | Empty docs may miss content |
| Template versioning | Full audit trail of learning | Slight storage overhead |
| Confidence tiers per line | Quality is transparent at every stage | Adds complexity to extraction |

---

## Extension Points

- **Swap `HybridSearch` for a vector DB** (Pinecone, Weaviate) or a cross-encoder reranker service — the retrieval interface is simple and pluggable.
- **Replace the template engine with an LLM** while preserving the retrieval/provenance/grounding-check interface — the `DraftPackage` structure stays the same.
- **Add layout-aware OCR** (layoutlm, docling) and table extraction behind the extractor layer — `ExtractedDocument` already supports structured fields.
- **Split edit learning into separate feedback channels** for extraction quality, retrieval ranking, and drafting style — the analyzer already produces per-pattern recommendations.
- **Add embedding-based semantic search** alongside TF-IDF — the `LightweightVectorIndex` class can be extended or replaced.
- **Connect the API to a frontend grounding inspector UI** — the `/inspect` endpoint already returns the support map.
- **Feed edit-learning corrections back into extraction** — missing-field patterns could update the structured extraction regex set.

