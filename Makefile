.PHONY: setup test extract draft learn evaluate demo api clean

PYTHON ?= python
CASES := case_a case_b case_c case_d
OUTPUT_DIR := samples/expected_outputs
CASE_DIR := samples/case_files

# ── Setup ──────────────────────────────────────────────────────────────
setup:
	python -m venv .venv
	@echo "Run: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (macOS/Linux)"
	@echo "Then: pip install -r requirements.txt"

# ── Tests ───────────────────────────────────────────────────────────────
test:
	$(PYTHON) -m unittest discover -s tests -v

# ── Extraction ─────────────────────────────────────────────────────────
extract: $(foreach c,$(CASES),extract-$(c))

extract-%:
	$(PYTHON) scripts/run_extraction.py \
		--input $(CASE_DIR)/$* \
		--output $(OUTPUT_DIR)/$*_extraction.json

# ── Draft generation ──────────────────────────────────────────────────
draft: $(foreach c,$(CASES),draft-$(c))

draft-%:
	$(PYTHON) scripts/generate_draft.py \
		--input $(CASE_DIR)/$* \
		--output $(OUTPUT_DIR)/$*_memo.md \
		--evidence-output $(OUTPUT_DIR)/$*_grounding.json

# ── Edit learning loop (case_a only) ──────────────────────────────────
learn:
	$(PYTHON) scripts/simulate_edit.py \
		--input $(CASE_DIR)/case_a \
		--draft-output $(OUTPUT_DIR)/case_a_original_memo.md \
		--edited-output $(OUTPUT_DIR)/case_a_operator_edit.md \
		--template-output data/templates_v2_learned.json
	$(PYTHON) scripts/generate_draft.py \
		--input $(CASE_DIR)/case_a \
		--output $(OUTPUT_DIR)/case_a_learned_memo.md \
		--template-path data/templates_v2_learned.json

# ── Evaluate all cases ────────────────────────────────────────────────
evaluate:
	$(PYTHON) scripts/evaluate_all.py \
		--input $(CASE_DIR) \
		--output $(OUTPUT_DIR)/evaluation_report.md

# ── Full end-to-end demo ─────────────────────────────────────────────
demo:
	$(PYTHON) scripts/run_case_demo.py \
		--input $(CASE_DIR)/case_a \
		--output-dir $(OUTPUT_DIR)

# ── API server ────────────────────────────────────────────────────────
api:
	uvicorn src.api.endpoints:app --reload --port 8000

# ── Clean runtime artifacts ───────────────────────────────────────────
clean:
	-del /q data\edits.jsonl 2>nul
	-del /q data\template_history.jsonl 2>nul
	@echo "Cleaned runtime artifacts"

# ── All outputs from scratch ───────────────────────────────────────────
all: extract draft learn evaluate
	@echo "=== All outputs regenerated ==="
