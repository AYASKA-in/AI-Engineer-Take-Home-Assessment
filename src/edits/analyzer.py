from __future__ import annotations

import difflib
import re

from src.schema import EditRecord


FORMAL_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b"
)

SECTION_HEADER_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

FORMAL_PHRASES = {
    "alleges", "contends", "asserts", "maintains", "furthermore",
    "notwithstanding", "pursuant to", "hereinafter", "whereas",
    "hereby", "aforementioned", "shall", "obligated",
}

INFORMAL_PHRASES = {
    "appears to", "seems like", "probably", "maybe", "looks like",
    "sort of", "kind of", "basically",
}

MISSING_FIELD_PATTERNS = {
    "section": re.compile(r"\bSection\s+\S+", re.IGNORECASE),
    "amount": re.compile(r"\$\d[\d,]*(?:\.\d{2})?"),
    "date": FORMAL_DATE_RE,
    "party": re.compile(r"\b(?:Plaintiff|Defendant|Claimant|Respondent|Buyer|Seller|Owner|Contractor):\s*\w+"),
}


def _extract_section_order(markdown: str) -> list[str]:
    return SECTION_HEADER_RE.findall(markdown)


def _detect_section_reordering(original: str, edited: str) -> tuple[bool, list[str] | None]:
    orig_order = _extract_section_order(original)
    edit_order = _extract_section_order(edited)
    if len(orig_order) != len(edit_order):
        return False, None
    if orig_order == edit_order:
        return False, None
    return True, edit_order


def _detect_phrasing_shift(original: str, edited: str) -> str | None:
    orig_lower = original.lower()
    edit_lower = edited.lower()
    formal_added = sum(1 for phrase in FORMAL_PHRASES if phrase in edit_lower and phrase not in orig_lower)
    informal_removed = sum(1 for phrase in INFORMAL_PHRASES if phrase in orig_lower and phrase not in edit_lower)
    if formal_added >= 2 or informal_removed >= 2:
        return "formal"
    informal_added = sum(1 for phrase in INFORMAL_PHRASES if phrase in edit_lower and phrase not in orig_lower)
    formal_removed = sum(1 for phrase in FORMAL_PHRASES if phrase in orig_lower and phrase not in edit_lower)
    if informal_added >= 2 or formal_removed >= 2:
        return "informal"
    return None


def _detect_missing_fields(original: str, edited: str) -> list[str]:
    missing = []
    for field_name, pattern in MISSING_FIELD_PATTERNS.items():
        orig_count = len(pattern.findall(original))
        edit_count = len(pattern.findall(edited))
        if edit_count > orig_count:
            missing.append(field_name)
    return missing


def _detect_retrieval_boost_candidates(original: str, edited: str) -> list[str]:
    added_lines = []
    for line in difflib.unified_diff(original.splitlines(), edited.splitlines(), lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:].strip())

    boost_terms: list[str] = []
    for line in added_lines:
        section_matches = re.findall(r"\bSection\s+(\S+)", line, re.IGNORECASE)
        boost_terms.extend(f"section {s.rstrip('.')}" for s in section_matches)
        amount_matches = re.findall(r"\$\d[\d,]*(?:\.\d{2})?", line)
        boost_terms.extend(amount_matches)
        date_matches = FORMAL_DATE_RE.findall(line)
        boost_terms.extend(date_matches)
    return list(dict.fromkeys(boost_terms))[:5]


def analyze_edit(case_id: str, original: str, edited: str) -> EditRecord:
    patterns: list[str] = []
    recommendations: list[str] = []

    original_sections = original.count("Section")
    edited_sections = edited.count("Section")
    if edited_sections > original_sections:
        patterns.append("added_section_specificity")
        recommendations.append("Prefer clause/section-level references when available.")

    original_citations = original.count("[")
    edited_citations = edited.count("[")
    if edited_citations > original_citations:
        patterns.append("increased_citation_density")
        recommendations.append("Increase evidence density in substantive memo sections.")

    if len(FORMAL_DATE_RE.findall(edited)) > len(FORMAL_DATE_RE.findall(original)):
        patterns.append("formalized_dates")
        recommendations.append("Render dates in formal legal style.")

    original_len = len(original.split())
    edited_len = len(edited.split())
    if edited_len > original_len * 1.08:
        patterns.append("expanded_claim_descriptions")
        recommendations.append("Expand terse allegation language with supporting detail.")

    reordered, new_order = _detect_section_reordering(original, edited)
    if reordered and new_order is not None:
        patterns.append("reordered_sections")
        recommendations.append(f"Section order preference detected: {' → '.join(new_order)}")

    phrasing = _detect_phrasing_shift(original, edited)
    if phrasing == "formal":
        patterns.append("formalized_phrasing")
        recommendations.append("Prefer formal legal phrasing in draft output.")
    elif phrasing == "informal":
        patterns.append("informal_phrasing")
        recommendations.append("Prefer more accessible phrasing in draft output.")

    missing_fields = _detect_missing_fields(original, edited)
    for field in missing_fields:
        patterns.append(f"missing_field_{field}")
        recommendations.append(f"Operator added {field} references that the system missed — improve {field} extraction or drafting.")

    boost_candidates = _detect_retrieval_boost_candidates(original, edited)
    if boost_candidates:
        patterns.append("retrieval_boost_candidates")
        recommendations.append(f"Consider boosting retrieval for: {', '.join(boost_candidates)}")

    diff_summary = list(difflib.unified_diff(original.splitlines(), edited.splitlines(), lineterm=""))
    metadata = {
        "diff_preview": diff_summary[:20],
        "section_order": new_order if reordered else None,
        "phrasing_preference": phrasing,
        "missing_fields": missing_fields,
        "retrieval_boost_candidates": boost_candidates,
    }

    return EditRecord(
        case_id=case_id,
        original_draft=original,
        edited_draft=edited,
        patterns_detected=patterns,
        recommendations=recommendations,
        metadata=metadata,
    )

