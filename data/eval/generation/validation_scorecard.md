# Golden QA Dataset Validation Scorecard

This report presents a thorough audit of the evaluation dataset `golden_qa.json` using `gemini-3.5-flash` on Vertex AI.

## Quality Summary

| Metric | Score / Count | Percentage |
| :--- | :---: | :---: |
| **Total Q&A Pairs Audited** | 72 | - |
| **Fully Valid Pairs** | 72 | **100.0%** |
| **Invalid/Flawed Pairs** | 0 | **0.0%** |
| **Valid Questions** | 72 / 72 | 100.0% |
| **Valid Answers** | 72 / 72 | 100.0% |
| **Citations Checked** | 191 | - |
| **Python Citation Match (Exact/Fuzzy)** | 175 / 191 | 91.62% |

---

## Detailed Audit Results

### Issue Breakdown

Below are the Q&A pairs identified with quality defects (invalid questions, answers, or missing/unsupported citations).


> [!NOTE]
> **Congratulations! All audited Q&A pairs are fully valid and supported by the source documentation.**
