from __future__ import annotations

import argparse
from pathlib import Path

from src.pipeline import generate_case_memo, save_extraction_output, save_grounding_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--template-path", default="data/templates_v1.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_id = Path(args.input).name

    documents, draft = generate_case_memo(args.input, template_path=args.template_path)
    save_extraction_output(output_dir / f"{case_id}_extraction.json", documents)
    (output_dir / f"{case_id}_memo.md").write_text(draft.memo_markdown, encoding="utf-8")
    save_grounding_output(output_dir / f"{case_id}_grounding.json", case_id, documents, draft)


if __name__ == "__main__":
    main()

