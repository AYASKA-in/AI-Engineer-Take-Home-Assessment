from __future__ import annotations

from src.schema import LineRecord


def group_lines(lines: list[LineRecord], window: int = 4) -> list[list[LineRecord]]:
    grouped: list[list[LineRecord]] = []
    current: list[LineRecord] = []
    for line in lines:
        if current and (len(current) >= window or line.page != current[-1].page):
            grouped.append(current)
            current = []
        current.append(line)
    if current:
        grouped.append(current)
    return grouped

