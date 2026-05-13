from __future__ import annotations

from pathlib import Path

from src.utils import dump_json


def write_markdown_report(path: str | Path, title: str, sections: dict[str, dict[str, object]]) -> None:
    lines = [f"# {title}", ""]
    for section, metrics in sections.items():
        lines.append(f"## {section}")
        for key, value in metrics.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    lines.append(f"- {key}.{nested_key}: {nested_value}")
            else:
                lines.append(f"- {key}: {value}")
        lines.append("")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_json_report(path: str | Path, payload: dict[str, object]) -> None:
    dump_json(path, payload)
