# Evaluation Report

## Per-case metrics

| Case | Avg confidence | Structured completeness | Usable chunk ratio | Noisy doc ratio | Evidence coverage | Unsupported claims | Unclear claims | Overall grounding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_a | 0.747 | 0.583 | 1.000 | 0.000 | 1.000 | 0 | 0 | GROUNDED |
| case_b | 0.960 | 0.625 | 1.000 | 0.000 | 1.000 | 0 | 0 | GROUNDED |
| case_c | 0.800 | 0.500 | 1.000 | 0.000 | 1.000 | 0 | 0 | GROUNDED |
| case_d | 0.640 | 0.000 | 1.000 | 0.000 | 0.714 | 2 | 0 | INSUFFICIENT_EVIDENCE |

## Grounding score detail

| Case | Citation precision | Unsupported rate | Unclear rate | Avg evidence conf | Grounded sections | Weak sections | Insufficient sections |
| --- | --- | --- | --- | --- | --- | --- | --- |
| case_a | 1.000 | 0.000 | 0.000 | 0.786 | 5 | 0 | 0 |
| case_b | 1.000 | 0.000 | 0.000 | 0.960 | 5 | 0 | 0 |
| case_c | 1.000 | 0.000 | 0.000 | 0.810 | 5 | 0 | 0 |
| case_d | 1.000 | 0.286 | 0.000 | 0.613 | 3 | 0 | 2 |

## Improvement loop

- Baseline substantive lines: 9
- Learned substantive lines: 12
- Baseline evidence coverage: 1.000
- Learned evidence coverage: 1.000
- Baseline overall grounding: GROUNDED
- Learned overall grounding: GROUNDED
- Template settings changed: min_evidence_per_section: 1 → 3, retrieval_boost_terms: [] → ['section', 'section 8', '$185,000', 'October 5, 1984', 'October 12, 1984', 'October 13, 1984']
