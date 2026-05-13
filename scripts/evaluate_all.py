from __future__ import annotations

import argparse
from pathlib import Path

from src.evaluation.metrics import draft_metrics, extraction_metrics
from src.pipeline import evaluation_bundle, generate_case_memo, simulate_learning
from src.utils import dump_json, load_json
from src.schema import DEFAULT_TEMPLATE_SETTINGS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    base = Path(args.input)
    rows: list[dict] = []
    for case_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        documents, draft = generate_case_memo(case_dir)
        bundle = evaluation_bundle(documents, draft)
        rows.append({"case_id": case_dir.name, **bundle})

    improvement = _improvement_demo("samples/case_files/case_a")
    _write_report(rows, improvement, args.output)


def _improvement_demo(case_dir: str) -> dict[str, object]:
    documents, baseline_draft = generate_case_memo(case_dir)
    baseline_metrics = draft_metrics(baseline_draft)
    baseline_memo = baseline_draft.memo_markdown

    ext_metrics = extraction_metrics(documents)

    edited_memo = _simulate_operator_edit(baseline_memo)
    simulate_learning(case_dir, baseline_memo, edited_memo, template_path="data/templates_v2_learned.json")

    _, learned_draft = generate_case_memo(case_dir, template_path="data/templates_v2_learned.json")
    learned_metrics = draft_metrics(learned_draft)

    return {
        "baseline_substantive_lines": baseline_metrics["substantive_lines"],
        "learned_substantive_lines": learned_metrics["substantive_lines"],
        "baseline_evidence_coverage": baseline_metrics["evidence_coverage"],
        "learned_evidence_coverage": learned_metrics["evidence_coverage"],
        "baseline_grounding": baseline_metrics.get("overall_grounding", "UNKNOWN"),
        "learned_grounding": learned_metrics.get("overall_grounding", "UNKNOWN"),
        "template_settings_changed": _diff_settings(
            _load_settings("data/templates_v1.json"),
            _load_settings("data/templates_v2_learned.json"),
        ),
    }


def _simulate_operator_edit(memo: str) -> str:
    lines = memo.splitlines()
    edited = []
    for line in lines:
        if "breach of contract" in line and "Section" not in line:
            line = line.replace("breach of contract", "breach of contract under Section 8")
        if "10/5/84" in line:
            line = line.replace("10/5/84", "October 5, 1984")
        if line.strip().startswith("-") and "[" in line:
            line = line + " [complaint_scan.ocr.txt p1:1-4]"
        edited.append(line)
    return "\n".join(edited)


def _diff_settings(before: dict, after: dict) -> list[str]:
    changes = []
    for key in sorted(set(before) | set(after)):
        b = before.get(key)
        a = after.get(key)
        if b != a:
            changes.append(f"{key}: {b!r} → {a!r}")
    return changes


def _load_settings(path: str) -> dict:
    return {**DEFAULT_TEMPLATE_SETTINGS, **load_json(path, DEFAULT_TEMPLATE_SETTINGS)}


def _write_report(rows: list[dict], improvement: dict[str, object], output_path: str) -> None:
    lines = ["# Evaluation Report\n"]
    lines.append("## Per-case metrics\n")
    lines.append("| Case | Avg confidence | Structured completeness | Usable chunk ratio | Noisy doc ratio | Evidence coverage | Unsupported claims | Unclear claims | Overall grounding |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        ext = row["extraction"]
        draft = row["draft"]
        grounding = row.get("grounding", {})
        lines.append(
            f"| {row['case_id']} "
            f"| {ext['average_confidence']:.3f} "
            f"| {ext['structured_completeness']:.3f} "
            f"| {ext['usable_chunk_ratio']:.3f} "
            f"| {ext.get('noisy_document_ratio', 0.0):.3f} "
            f"| {grounding.get('evidence_coverage', draft.get('evidence_coverage', 0.0)):.3f} "
            f"| {draft.get('unsupported_claims', 0)} "
            f"| {draft.get('unclear_claims', 0)} "
            f"| {draft.get('overall_grounding', grounding.get('overall_status', 'N/A'))} |"
        )

    lines.append("\n## Grounding score detail\n")
    lines.append("| Case | Citation precision | Unsupported rate | Unclear rate | Avg evidence conf | Grounded sections | Weak sections | Insufficient sections |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        g = row.get("grounding", {})
        lines.append(
            f"| {row['case_id']} "
            f"| {g.get('citation_precision', 0.0):.3f} "
            f"| {g.get('unsupported_claim_rate', 0.0):.3f} "
            f"| {g.get('unclear_claim_rate', 0.0):.3f} "
            f"| {g.get('avg_evidence_confidence', 0.0):.3f} "
            f"| {g.get('sections_grounded', 0)} "
            f"| {g.get('sections_weak', 0)} "
            f"| {g.get('sections_insufficient', 0)} |"
        )

    lines.append("\n## Improvement loop\n")
    lines.append(f"- Baseline substantive lines: {improvement['baseline_substantive_lines']}")
    lines.append(f"- Learned substantive lines: {improvement['learned_substantive_lines']}")
    lines.append(f"- Baseline evidence coverage: {improvement['baseline_evidence_coverage']:.3f}")
    lines.append(f"- Learned evidence coverage: {improvement['learned_evidence_coverage']:.3f}")
    lines.append(f"- Baseline overall grounding: {improvement['baseline_grounding']}")
    lines.append(f"- Learned overall grounding: {improvement['learned_grounding']}")
    lines.append(f"- Template settings changed: {', '.join(improvement['template_settings_changed'])}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
