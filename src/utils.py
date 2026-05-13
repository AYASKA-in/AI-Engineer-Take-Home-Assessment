from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9$][A-Za-z0-9$./-]*")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sentence_split(text: str) -> list[str]:
    protected = text
    replacements = {
        "Inc.": "Inc<prd>",
        "No.": "No<prd>",
        "Sec.": "Sec<prd>",
        "J.": "J<prd>",
    }
    for original, placeholder in replacements.items():
        protected = protected.replace(original, placeholder)
    parts = re.split(r"(?<=[.!?])\s+", normalize_whitespace(protected))
    restored = []
    for part in parts:
        for original, placeholder in replacements.items():
            part = part.replace(placeholder, original)
        restored.append(part)
    return [part.strip() for part in restored if part.strip()]


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def cosine_similarity(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    numerator = sum(a[token] * b[token] for token in common)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return numerator / (norm_a * norm_b)


def dump_json(path: str | Path, payload: object) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json(path: str | Path, default: object) -> object:
    file_path = Path(path)
    if not file_path.exists():
        return default
    return json.loads(file_path.read_text(encoding="utf-8"))
