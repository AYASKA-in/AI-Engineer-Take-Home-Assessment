from __future__ import annotations

import argparse
from pathlib import Path

from src.pipeline import generate_case_memo, simulate_learning


def synthetic_operator_edit(markdown: str) -> str:
    edited = markdown.replace(
        "breach",
        "breach of contract under Section 8",
    )
    edited = edited.replace("10/05/84", "October 5, 1984")
    lines = []
    for line in edited.splitlines():
        if line.startswith("- ") and "[" in line and "Section 8" in line and line.count("[") == 1:
            line = line + f" {line[line.index('['):]}"
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--draft-output", required=True)
    parser.add_argument("--edited-output", required=True)
    parser.add_argument("--template-output", default="data/templates_v2_learned.json")
    args = parser.parse_args()

    _, draft = generate_case_memo(args.input)
    edited = synthetic_operator_edit(draft.memo_markdown)
    Path(args.draft_output).write_text(draft.memo_markdown, encoding="utf-8")
    Path(args.edited_output).write_text(edited, encoding="utf-8")
    simulate_learning(args.input, draft.memo_markdown, edited, template_path=args.template_output)


if __name__ == "__main__":
    main()
