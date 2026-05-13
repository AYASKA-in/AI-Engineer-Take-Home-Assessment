from __future__ import annotations

import argparse
from pathlib import Path

from src.pipeline import generate_case_memo, save_grounding_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--template-path", default="data/templates_v1.json")
    parser.add_argument("--evidence-output")
    args = parser.parse_args()

    documents, draft = generate_case_memo(args.input, template_path=args.template_path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft.memo_markdown, encoding="utf-8")
    if args.evidence_output:
        save_grounding_output(args.evidence_output, Path(args.input).name, documents, draft)


if __name__ == "__main__":
    main()

