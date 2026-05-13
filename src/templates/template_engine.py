from __future__ import annotations

from pathlib import Path
import re

from src.retrieval.hybrid_search import HybridSearch
from src.schema import (
    DEFAULT_TEMPLATE_SETTINGS,
    DraftPackage,
    ExtractedDocument,
    GroundingStatus,
    RetrievalResult,
    SectionGrounding,
    classify_confidence,
)
from src.templates.confidence_report import build_confidence_report
from src.utils import load_json


class TemplateEngine:
    SECTION_QUERIES = {
        "Matter overview": "dispute contract breach notice project services payment agreement",
        "Key parties": "plaintiff defendant claimant respondent owner contractor lender buyer seller parties",
        "Timeline": "date signed notice deadline invoice inspection chronology",
        "Allegations and obligations": "breach failed shall must obligated required section clause notice",
        "Open questions": "missing unclear illegible redacted disputed absent not provided",
    }

    def __init__(self, template_path: str | Path = "data/templates_v1.json") -> None:
        loaded = load_json(template_path, DEFAULT_TEMPLATE_SETTINGS)
        self.settings = {**DEFAULT_TEMPLATE_SETTINGS, **loaded}

    def _ordered_sections(self) -> list[tuple[str, str]]:
        preferred_order = self.settings.get("section_order", list(self.SECTION_QUERIES.keys()))
        ordered = []
        for section in preferred_order:
            if section in self.SECTION_QUERIES:
                ordered.append((section, self.SECTION_QUERIES[section]))
        for section, query in self.SECTION_QUERIES.items():
            if section not in preferred_order:
                ordered.append((section, query))
        return ordered

    def _augment_query(self, query: str) -> str:
        boost_terms = self.settings.get("retrieval_boost_terms", [])
        if not boost_terms:
            return query
        return f"{query} {' '.join(boost_terms)}"

    def _check_extraction_noise(self, documents: list[ExtractedDocument]) -> tuple[bool, list[str]]:
        min_confidence = self.settings.get("min_extraction_confidence", 0.45)
        warnings: list[str] = []
        all_noisy = True
        for doc in documents:
            if doc.average_confidence >= min_confidence:
                all_noisy = False
            if doc.average_confidence < min_confidence:
                warnings.append(
                    f"{doc.source_path}: extraction confidence {doc.average_confidence:.2f} "
                    f"is below threshold {min_confidence:.2f} — content may be unreliable"
                )
            for region in doc.skipped_regions:
                warnings.append(
                    f"{doc.source_path} p{region['page']}:{region['line_start']}-{region['line_end']}: "
                    f"{region['reason']}"
                )
        return all_noisy, warnings

    def _classify_section_grounding(
        self, section: str, evidence: list[RetrievalResult], documents: list[ExtractedDocument]
    ) -> SectionGrounding:
        min_score = self.settings.get("min_retrieval_score", 0.15)
        valid_evidence = [r for r in evidence if r.score >= min_score]
        avg_conf = (
            sum(r.chunk.confidence for r in valid_evidence) / len(valid_evidence)
            if valid_evidence
            else 0.0
        )
        top_score = valid_evidence[0].score if valid_evidence else 0.0

        if not valid_evidence:
            status = GroundingStatus.INSUFFICIENT_EVIDENCE
            reason = "No evidence chunks above minimum retrieval score"
        elif len(valid_evidence) < self.settings["min_evidence_per_section"]:
            status = GroundingStatus.WEAK_EVIDENCE
            reason = (
                f"Only {len(valid_evidence)} evidence chunk(s) found; "
                f"minimum is {self.settings['min_evidence_per_section']}"
            )
        elif avg_conf < 0.55:
            status = GroundingStatus.EXTRACTION_TOO_NOISY
            reason = f"Average source confidence {avg_conf:.2f} is low — evidence may be unreliable"
        else:
            status = GroundingStatus.GROUNDED
            reason = ""

        return SectionGrounding(
            section_name=section,
            status=status,
            evidence_count=len(valid_evidence),
            top_score=round(top_score, 4),
            avg_confidence=round(avg_conf, 3),
            reason=reason,
        )

    def _mark_unclear_text(self, text: str, confidence: float) -> str:
        tier = classify_confidence(confidence)
        if tier.value in ("LOW", "UNREADABLE"):
            return f"[UNCLEAR:{tier.value}] {text}"
        return text

    def generate(
        self,
        case_id: str,
        documents: list[ExtractedDocument],
        retriever: HybridSearch,
    ) -> DraftPackage:
        all_noisy, extraction_warnings = self._check_extraction_noise(documents)

        section_evidence: dict[str, list[RetrievalResult]] = {}
        section_grounding_list: list[SectionGrounding] = []
        lines = [f"# First-Pass Internal Memo: {case_id}", ""]

        if all_noisy and self.settings.get("abstain_on_insufficient_evidence", True):
            lines.append("## Grounding Notice")
            lines.append(
                "- **INSUFFICIENT EVIDENCE**: All source documents have extraction confidence below the "
                "usable threshold. This draft is withheld to avoid unsupported claims. "
                "Please provide higher-quality scans or verified transcriptions."
            )
            lines.append("")
            for doc in documents:
                lines.append(f"- {doc.source_path}: confidence {doc.average_confidence:.2f} "
                             f"({classify_confidence(doc.average_confidence).value})")
            memo = "\n".join(lines).strip() + "\n"
            return DraftPackage(
                memo_markdown=memo,
                section_evidence={},
                metrics={"substantive_lines": 0, "cited_lines": 0, "evidence_coverage": 0.0, "unsupported_claims": 0},
                section_grounding=[],
                overall_grounding_status=GroundingStatus.EXTRACTION_TOO_NOISY,
                extraction_warnings=extraction_warnings,
            )

        if extraction_warnings:
            lines.append("## Extraction Quality Notes")
            for warning in extraction_warnings:
                lines.append(f"- {warning}")
            lines.append("")

        lines.append("## Summary")
        summary_query = self._augment_query(
            "main dispute breach contract allegations obligations dates parties missing issues"
        )
        summary_evidence = retriever.search(
            summary_query,
            top_k=max(self.settings["min_evidence_per_section"] + 2, 5),
        )
        section_evidence["Summary"] = summary_evidence
        for bullet in self._summary_bullets(documents, summary_evidence):
            lines.append(f"- {bullet}")
        lines.append("")

        for section, query in self._ordered_sections():
            augmented = self._augment_query(query)
            evidence = retriever.search(augmented, top_k=self.settings["min_evidence_per_section"] + 1)
            section_evidence[section] = evidence
            grounding = self._classify_section_grounding(section, evidence, documents)
            section_grounding_list.append(grounding)
            lines.append(f"## {section}")

            if grounding.status == GroundingStatus.INSUFFICIENT_EVIDENCE:
                lines.append(
                    f"- **INSUFFICIENT EVIDENCE**: No reliable source evidence was found for this section. "
                    f"Draft withheld to avoid unsupported claims. [{grounding.reason}]"
                )
            elif grounding.status == GroundingStatus.WEAK_EVIDENCE:
                lines.append(
                    f"- *Weak evidence*: {grounding.reason}. Treat the following with caution."
                )
                bullets = self._section_bullets(section, documents, evidence)
                lines.extend(f"- {bullet}" for bullet in bullets)
            elif grounding.status == GroundingStatus.EXTRACTION_TOO_NOISY:
                lines.append(
                    f"- *Noisy source*: {grounding.reason}. The underlying text may be unreliable."
                )
                bullets = self._section_bullets(section, documents, evidence)
                lines.extend(f"- {bullet}" for bullet in bullets)
            else:
                bullets = self._section_bullets(section, documents, evidence)
                lines.extend(f"- {bullet}" for bullet in bullets)
            lines.append("")

        memo = "\n".join(lines).strip() + "\n"
        metrics = build_confidence_report(memo)

        overall_status = GroundingStatus.GROUNDED
        if any(sg.status == GroundingStatus.INSUFFICIENT_EVIDENCE for sg in section_grounding_list):
            overall_status = GroundingStatus.INSUFFICIENT_EVIDENCE
        elif any(sg.status in (GroundingStatus.WEAK_EVIDENCE, GroundingStatus.EXTRACTION_TOO_NOISY)
                 for sg in section_grounding_list):
            overall_status = GroundingStatus.WEAK_EVIDENCE

        return DraftPackage(
            memo_markdown=memo,
            section_evidence=section_evidence,
            metrics=metrics,
            section_grounding=section_grounding_list,
            overall_grounding_status=overall_status,
            extraction_warnings=extraction_warnings,
        )

    def _summary_bullets(
        self,
        documents: list[ExtractedDocument],
        evidence: list[RetrievalResult],
    ) -> list[str]:
        bullets: list[str] = []
        parties = []
        dates = []
        allegations = []
        open_questions = []
        for doc in documents:
            parties.extend(doc.structured_fields.get("parties", []))
            dates.extend(doc.structured_fields.get("dates", []))
            allegations.extend(doc.structured_fields.get("allegations", []))
            open_questions.extend(
                warning for warning in doc.warnings if any(token in warning.lower() for token in ("unclear", "illegible", "redacted"))
            )

        unique_parties = list(dict.fromkeys(parties))[:2]
        allegation_evidence = self._find_evidence(
            evidence,
            preferred_terms=("breach", "failed", "default"),
        )
        timeline_evidence = self._find_evidence(
            evidence,
            preferred_terms=("october", "march", "july", "date", "signed"),
        )
        ambiguity_evidence = self._find_evidence(
            evidence,
            preferred_terms=("unclear", "illegible", "missing", "absent", "redacted"),
        )

        if unique_parties and allegations and allegation_evidence is not None:
            allegation_text = min(allegations, key=len)
            allegation_text = allegation_text.replace("The plaintiff alleges ", "")
            allegation_text = allegation_text[0].lower() + allegation_text[1:] if allegation_text else allegation_text
            citation = allegation_evidence.chunk.citation
            if allegation_evidence.chunk.confidence < 0.55:
                citation = f"{citation} ⚠ LOW-CONF SOURCE"
            bullets.append(
                f"This bundle appears to center on a dispute between {' and '.join(unique_parties)} "
                f"with allegations tied to {allegation_text} [{citation}]"
            )
        if dates and timeline_evidence is not None:
            formatted = [self._format_date(date) for date in list(dict.fromkeys(dates))[:2]]
            citation = timeline_evidence.chunk.citation
            if timeline_evidence.chunk.confidence < 0.55:
                citation = f"{citation} ⚠ LOW-CONF SOURCE"
            bullets.append(
                f"Key chronology markers include {', '.join(formatted)}, which likely frame the initial review timeline. [{citation}]"
            )
        if open_questions and ambiguity_evidence is not None:
            bullets.append(
                f"The source set contains ambiguity signals that warrant manual review before relying on any final legal conclusion. [{ambiguity_evidence.chunk.citation}]"
            )
        return bullets[:3]

    def _section_bullets(
        self,
        section: str,
        documents: list[ExtractedDocument],
        evidence: list[RetrievalResult],
    ) -> list[str]:
        if section == "Key parties":
            parties = []
            for doc in documents:
                parties.extend(doc.structured_fields.get("parties", []))
            unique = list(dict.fromkeys(parties))[:4]
            if unique and evidence:
                return [f"Parties identified in the file include {', '.join(unique)}. [{evidence[0].chunk.citation}]"]
        if section == "Timeline":
            dates = []
            for doc in documents:
                dates.extend(doc.structured_fields.get("dates", []))
            unique_dates = [self._format_date(date) for date in list(dict.fromkeys(dates))[:4]]
            if unique_dates and evidence:
                return [
                    f"Dates repeatedly referenced in the bundle include {', '.join(unique_dates)}. "
                    f"[{evidence[0].chunk.citation}]"
                ]
        if section == "Allegations and obligations":
            allegations = []
            obligations = []
            for doc in documents:
                allegations.extend(doc.structured_fields.get("allegations", []))
                obligations.extend(doc.structured_fields.get("obligations", []))
            bullets = []
            if allegations:
                allegation = allegations[0]
                if self.settings["claim_detail_expansion"] != "low" and "section" not in allegation.lower():
                    for result in evidence:
                        if "section" in result.chunk.text.lower():
                            allegation = f"{allegation} The file also ties the issue to {result.chunk.text}"
                            break
                bullets.append(f"{allegation} [{evidence[0].chunk.citation}]")
            if obligations:
                obligation_evidence = next(
                    (result for result in evidence if any(token in result.chunk.text.lower() for token in ("shall", "required", "must"))),
                    evidence[0] if evidence else None,
                )
                if obligation_evidence is not None:
                    bullets.append(f"{obligations[0]} [{obligation_evidence.chunk.citation}]")
            if bullets:
                return bullets

        if section == "Open questions" and evidence:
            filtered = [
                result
                for result in evidence
                if any(token in result.chunk.text.lower() for token in ("unclear", "illegible", "redacted", "missing", "no "))
            ]
            chosen = filtered[: self.settings["min_evidence_per_section"]] or evidence[:1]
            return [f"{result.chunk.text} [{result.chunk.citation}]" for result in chosen]

        if evidence:
            bullets = []
            for result in evidence[: self.settings["min_evidence_per_section"]]:
                text = result.chunk.text
                if result.chunk.confidence < 0.55:
                    text = f"[UNCLEAR] {text}"
                bullets.append(f"{text} [{result.chunk.citation}]")
            return bullets

        fallback = "[No supporting evidence found — draft withheld for this section]"
        if section == "Open questions" and self.settings["include_open_questions"]:
            return [f"Some source material appears incomplete or ambiguous and should be reviewed manually. {fallback}"]
        return [fallback]

    def _format_date(self, value: str) -> str:
        if not self.settings.get("prefer_formal_dates", True):
            return value
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", value)
        if not match:
            return value
        month, day, year = match.groups()
        year_num = int(year)
        if year_num < 100:
            year_num += 1900 if year_num >= 50 else 2000
        months = {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December",
        }
        return f"{months[int(month)]} {int(day)}, {year_num}"

    def _find_evidence(
        self,
        evidence: list[RetrievalResult],
        preferred_terms: tuple[str, ...],
    ) -> RetrievalResult | None:
        for result in evidence:
            lowered = result.chunk.text.lower()
            if any(term in lowered for term in preferred_terms):
                return result
        return evidence[0] if evidence else None
