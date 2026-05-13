from __future__ import annotations

import re


def memo_lines_with_citations(markdown: str) -> tuple[int, int]:
    substantive = 0
    cited = 0
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("-"):
            substantive += 1
            if re.search(r"\[[^\]]+ p\d+:\d+-\d+\]", stripped):
                cited += 1
    return substantive, cited


def unsupported_lines(markdown: str) -> list[str]:
    flagged = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        if "[No supporting evidence found" in stripped:
            flagged.append(stripped)
        if "**INSUFFICIENT EVIDENCE**" in stripped:
            flagged.append(stripped)
    return flagged


def unclear_lines(markdown: str) -> list[str]:
    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("-") and ("[UNCLEAR" in stripped or "LOW-CONF" in stripped):
            lines.append(stripped)
    return lines

