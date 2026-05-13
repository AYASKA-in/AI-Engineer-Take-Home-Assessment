from __future__ import annotations

from pathlib import Path

from src.schema import DEFAULT_TEMPLATE_SETTINGS, EditRecord
from src.utils import dump_json, load_json


def apply_edit_learning(record: EditRecord, template_path: str | Path = "data/templates_v1.json") -> dict[str, object]:
    settings = {
        **DEFAULT_TEMPLATE_SETTINGS,
        **load_json(template_path, DEFAULT_TEMPLATE_SETTINGS),
    }

    if "formalized_dates" in record.patterns_detected:
        settings["prefer_formal_dates"] = True
    if "added_section_specificity" in record.patterns_detected:
        settings["require_section_citations"] = True
    if "expanded_claim_descriptions" in record.patterns_detected:
        settings["claim_detail_expansion"] = "high"
    if "increased_citation_density" in record.patterns_detected:
        settings["min_evidence_per_section"] = max(int(settings["min_evidence_per_section"]), 3)

    if "reordered_sections" in record.patterns_detected:
        new_order = record.metadata.get("section_order")
        if new_order and isinstance(new_order, list):
            current_order = settings.get("section_order", [])
            if new_order != current_order:
                settings["section_order"] = new_order

    if "formalized_phrasing" in record.patterns_detected:
        settings["phrasing_style"] = "formal"
    elif "informal_phrasing" in record.patterns_detected:
        settings["phrasing_style"] = "informal"

    for pattern in record.patterns_detected:
        if pattern.startswith("missing_field_"):
            field_name = pattern.replace("missing_field_", "")
            existing_boosts = settings.get("retrieval_boost_terms", [])
            if field_name not in existing_boosts:
                existing_boosts.append(field_name)
            settings["retrieval_boost_terms"] = existing_boosts

    if "retrieval_boost_candidates" in record.patterns_detected:
        candidates = record.metadata.get("retrieval_boost_candidates", [])
        existing_boosts = list(settings.get("retrieval_boost_terms", []))
        for candidate in candidates:
            if candidate not in existing_boosts:
                existing_boosts.append(candidate)
        settings["retrieval_boost_terms"] = existing_boosts

    dump_json(template_path, settings)
    return settings

