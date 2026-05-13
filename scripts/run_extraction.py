from __future__ import annotations

import argparse

from src.pipeline import run_extraction, save_extraction_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    documents = run_extraction(args.input)
    save_extraction_output(args.output, documents)


if __name__ == "__main__":
    main()

