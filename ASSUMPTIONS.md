# Assumptions and Tradeoffs

## Assumptions

1. **Reviewers may not want to install system OCR dependencies** just to inspect the submission. The sample corpus uses `.ocr.txt` text sidecars so the entire pipeline runs deterministically without Tesseract or any external binary.

2. **Grounding and inspectability matter more than high-fluency prose** for this task. A draft that honestly says "insufficient evidence" is more valuable than one that fabricates confident-sounding claims.

3. **Synthetic legal-style samples are acceptable** if they demonstrate noisy-input handling and evidence-backed drafting. The four sample cases cover clean text, OCR artifacts, mixed formats, and deliberately nasty input.

4. **A practical system should be easy to run from a local Python environment** with minimal setup. The venv + pip install flow is intentionally simple. Docker is provided as an alternative.

5. **It is better to say "insufficient evidence" than to produce a confident but unsupported draft.** This is the core design principle driving the abstain behavior.

6. **Reviewers will value seeing the system handle failure modes**, not just success cases. case_d exists specifically to demonstrate graceful degradation.

7. **Per-line confidence tiers are a reasonable proxy for extraction quality** when ground-truth OCR accuracy is unavailable. The thresholds (0.85 / 0.65 / 0.45) were chosen to be conservative on the LOW/UNREADABLE boundary.

8. **Date-pattern reranking is a legitimate retrieval signal** for legal documents. When a section query contains date-related terms (timeline, chronology, deadline) and a chunk contains date patterns, the chunk deserves a relevance bonus even without direct lexical overlap. This was added after observing that case_b's Timeline section had zero retrieval hits without it.

9. **Template versioning is worth the storage overhead** because it provides a complete audit trail of what the system learned and when — critical for a system that modifies its own behavior from operator feedback.

---

## Tradeoffs

### Rule-based field extraction vs. learned IE model
- **Benefit**: Transparent, deterministic, and easy to audit. No training data needed.
- **Cost**: Weaker recall on highly variable entity formats (e.g. unusual date formats, non-standard party names).

### Lightweight in-memory retrieval vs. FAISS / Elasticsearch
- **Benefit**: Zero infra, instant setup, simpler reviewer experience.
- **Cost**: Not scalable to massive corpora. TF-IDF is a weaker semantic signal than dense embeddings.

### Template engine vs. external LLM
- **Benefit**: No hallucination risk outside retrieved evidence. No API dependency. Runs fully offline. Deterministic outputs.
- **Cost**: Less expressive writing. Weaker abstraction over scattered facts. Cannot synthesize across distant evidence chunks.

### Strict abstain behavior vs. always producing a draft
- **Benefit**: Prevents unsupported claims. Demonstrates disciplined grounding. Reviewer can trust that any content in the draft is backed by evidence.
- **Cost**: Some sections or entire cases produce no draft content when evidence is weak (e.g. case_d has 2 INSUFFICIENT_EVIDENCE sections).

### Edit-learning targets draft behavior vs. full pipeline feedback
- **Benefit**: Clearly demonstrates reusable improvement from edits across multiple dimensions (section ordering, phrasing style, retrieval boosts, evidence density, missing fields).
- **Cost**: Does not yet feed corrections back into extraction accuracy or ranking weights. Missing-field patterns update retrieval boost terms but don't change the regex extraction rules.

### Citation validation against actual source lines vs. pattern-matching
- **Benefit**: Citation precision is a real metric, not an inflated one. A citation `[doc.txt p1:5-8]` is only counted as valid if those lines actually exist in the extracted document.
- **Cost**: Slightly more complex evaluation code. Precision scores are lower on edge cases where line numbers shift during extraction.

### Per-line confidence tiers vs. document-level confidence
- **Benefit**: Granular quality signal that enables per-section grounding checks and unclear-content markers.
- **Cost**: More complex extraction pipeline. Each line needs individual scoring.

### Date-pattern reranking bonus vs. pure lexical/semantic retrieval
- **Benefit**: Fixes retrieval gaps on small corpora where section queries have no direct lexical overlap with chunks. case_b's Timeline section went from INSUFFICIENT_EVIDENCE to GROUNDED.
- **Cost**: Adds a heuristic signal that could over-boost irrelevant chunks containing dates in unrelated contexts. The +0.06 bonus is intentionally modest to limit this risk.

### Virtual environment setup vs. system-wide install
- **Benefit**: Isolated dependencies, reproducible environment, no conflicts with system Python packages.
- **Cost**: Extra setup step for the reviewer. Mitigated by clear instructions in README.

---

## What I Would Do With More Time

1. **Feed edit-learning corrections back into extraction**: missing-field patterns could update the structured extraction regex set, not just retrieval boost terms.
2. **Add dense embedding-based semantic search** (e.g. sentence-transformers) alongside TF-IDF for better retrieval on paraphrased queries.
3. **Build a frontend grounding inspector UI** that visualizes the support map — the `/inspect` API endpoint already returns the data.
4. **Replace the template engine with an LLM** while preserving the retrieval/provenance/grounding-check interface. The `DraftPackage` structure is designed to be LLM-agnostic.
5. **Add layout-aware OCR** (layoutlm, docling) and table extraction behind the extractor layer.
6. **Implement cross-case learning**: when the system learns from edits on case_a, those preferences should transfer to case_b/c/d drafts as well.

