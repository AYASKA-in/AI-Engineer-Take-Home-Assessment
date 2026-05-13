from __future__ import annotations

import re
from collections import Counter

from src.utils import normalize_whitespace, sentence_split


DATE_PATTERNS = [
    re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
]
MONEY_RE = re.compile(r"\$\d[\d,]*(?:\.\d{2})?")
SECTION_RE = re.compile(r"\b(?:Section|Sec\.|Clause)\s+[A-Za-z0-9.\-]+\b", re.IGNORECASE)
PARTY_RE = re.compile(
    r"\b(?:Plaintiff|Defendant|Claimant|Respondent|Owner|Contractor|Insurer|Lender|Buyer|Seller)\b:\s*([A-Z][A-Za-z0-9&.,' -]{2,80})",
    re.IGNORECASE,
)
ORG_RE = re.compile(
    r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:LLC|Inc\.|Inc|Partners|Services|Holdings|Group))\b"
)


def extract_structured_fields(text: str) -> dict[str, object]:
    clean = normalize_whitespace(text)
    line_units = [normalize_whitespace(line) for line in text.splitlines() if line.strip()]
    sentences = sentence_split(text)
    candidate_units = list(dict.fromkeys(line_units + sentences))
    dates: list[str] = []
    for pattern in DATE_PATTERNS:
        dates.extend(pattern.findall(text))

    parties = [normalize_whitespace(match).strip(" ,.") for match in PARTY_RE.findall(text)]
    parties.extend(normalize_whitespace(match).strip(" ,.") for match in ORG_RE.findall(text))
    sections = [normalize_whitespace(match) for match in SECTION_RE.findall(text)]
    amounts = MONEY_RE.findall(text)

    allegations = [
        sentence
        for sentence in candidate_units
        if any(
            token in sentence.lower()
            for token in ("alleges", "breach", "failed", "did not", "default", "notice")
        )
    ]
    obligations = [
        sentence
        for sentence in candidate_units
        if any(
            token in sentence.lower()
            for token in ("shall", "must", "required", "obligated", "deliver")
        )
    ]

    filtered_parties = []
    for item in parties:
        lowered = item.lower()
        if any(token in lowered for token in ("alleges", "signed", "observed", "spoke", "representative absent", "says")):
            continue
        filtered_parties.append(item)
    normalized_parties = sorted(dict.fromkeys(filtered_parties))

    field_counts = Counter({
        "dates": len(dates),
        "parties": len(normalized_parties),
        "sections": len(sections),
        "amounts": len(amounts),
    })

    return {
        "dates": sorted(set(dates)),
        "parties": normalized_parties[:12],
        "sections": sorted(set(sections)),
        "amounts": sorted(set(amounts)),
        "allegations": allegations[:8],
        "obligations": obligations[:8],
        "field_counts": dict(field_counts),
    }
