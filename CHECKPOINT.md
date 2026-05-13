# Submission Checkpoint

## Current status

- Core end-to-end pipeline is implemented and runnable.
- Synthetic messy legal bundles are included for `case_a`, `case_b`, `case_c`, and `case_d`.
- Grounded first-pass memo generation is working with page:line citations.
- **Abstain behavior**: the system withholds drafts when evidence is insufficient or extraction is too noisy.
- Grounding is exported as an inspectable JSON support map with per-section grounding status.
- Edit-learning demo is working and persists learned template behavior with version history.
- **Confidence tiers** (HIGH/MEDIUM/LOW/UNREADABLE) are assigned to every extracted line.
- **Unclear markers** flag lines containing `[illegible]`, `???`, `[unreadable]`, etc.
- **Fallback chains** handle extraction failures gracefully (PDF → OCR → empty doc with warnings).
- **Rich edit analysis** detects section reordering, phrasing shifts, missing fields, and retrieval boost candidates.
- **Template versioning** records every learning event with timestamp and settings snapshot.
- **Grounding metrics** are computed with citation validation against actual source lines.
- **FastAPI endpoints** expose the pipeline as a REST API.
- **Docker setup** included for reviewer convenience.
- Automated tests now cover 39 test cases across 6 test files.

## Latest completed work

- Added abstain/fallback behavior: system says "INSUFFICIENT EVIDENCE" instead of guessing.
- Added confidence tiers and unclear markers to extraction pipeline.
- Added skipped-region detection in extractors.
- Added `GroundingStatus` enum and per-section grounding classification.
- Added `compute_grounding_score` with citation validation against source lines.
- Added richer edit analysis: section reordering, phrasing shifts, missing fields, retrieval boosts.
- Added template versioning (`data/template_history.jsonl`).
- Added `case_d` edge case with deliberately nasty input.
- Added FastAPI wrapper with 7 endpoints.
- Added Dockerfile and docker-compose.yml.
- Added 4 new test files: `test_confidence.py`, `test_grounding.py`, `test_edit_learning.py`, `test_abstain.py`.
- Updated all documentation.

## Validation

- `python -m unittest discover -s tests -v` passed with 39/39 tests.
- Core scripts ran successfully:
  - `scripts/run_extraction.py`
  - `scripts/generate_draft.py`
  - `scripts/run_case_demo.py`
  - `scripts/evaluate_all.py`
  - `scripts/simulate_edit.py`

## Remaining polish opportunities

- Replace the heuristic retrieval layer with a stronger embedding/reranking stack if external dependencies are acceptable.
- Add a frontend grounding inspector UI.
- Feed edit-learning corrections back into extraction accuracy or ranking weights.
