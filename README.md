Questionnaire Scoring Agent
Automatically score questionnaire quality using Claude.

Quick Start
1. Install Dependencies
bash
pip install -r requirements.txt
2. Set API Key
bash
export ANTHROPIC_API_KEY='your-api-key-here'
3. Score a Document
bash
python questionnaire_scorer.py path/to/your/survey.docx
Output:

=== SCORING RESULTS ===

Found 4 questions
Sections: Demographics, Product Feedback

Section Averages:

Demographics:
  clarity: 5.00
  specificity: 5.00
  bias: 5.00
  actionability: 3.00

Product Feedback:
  clarity: 4.50
  specificity: 3.00
  bias: 3.50
  actionability: 3.50

Full results saved to scoring_results.json
Running Evals
1. Create Test Questionnaires
Create a test_questionnaires/ directory with sample DOCX files:

test_questionnaires/
├── simple_survey.docx
├── biased_survey.docx
└── vague_survey.docx
Example content for simple_survey.docx:

Demographics

1. What is your age?
2. What is your gender?

Product Feedback

1. How satisfied are you with our amazing product?
2. Would you recommend us to others?
2. Create Ground Truth Dataset
Edit sample_eval_dataset.json with expected scores for your test documents.

3. Run Evals
bash
python eval_harness.py sample_eval_dataset.json
Output shows:

Per-eval metrics
Aggregate performance
Pass/fail against thresholds
4. Tune Until Passing
If evals fail:

Check extraction errors: Did it miss questions?
Update prompt to handle your document format better
Check scoring inconsistency: High MAE?
Add few-shot examples to the prompt
Tighten rubric definitions
Iterate: Update SCORING_PROMPT in questionnaire_scorer.py
Re-run: python eval_harness.py sample_eval_dataset.json
Eval Metrics Explained
extraction_accuracy: % of questions found (target: ≥95%)
{attribute}_mae: Mean absolute error for scores (target: ≤0.5-0.8)
{attribute}_within_1: % scores within ±1 point (target: ≥85%)
section_detection: % sections correctly identified (target: ≥95%)
Customizing Scoring Attributes
Edit the SCORING_PROMPT in questionnaire_scorer.py:

python
SCORING_PROMPT = """
...
2. **Score each question** on these attributes (1-5 scale):
   - YourAttribute: Description here
     * 5 = Best case
     * 3 = Middle case
     * 1 = Worst case
...
"""
Then update:

CSV column names in the prompt
_parse_csv_output() to handle new attributes
Eval dataset expected outputs
THRESHOLDS in eval_harness.py
Files
questionnaire_scorer.py - Main agent
eval_harness.py - Evaluation runner
sample_eval_dataset.json - Ground truth data
requirements.txt - Dependencies
Supported Formats
.docx (Word documents)
.pdf (PDFs)
Google Docs (export as DOCX first)
Next Steps
Expand eval dataset: Add 10-15 diverse examples
Add failure analysis: Log specific question mismatches
Version prompts: Track prompt changes and eval scores over time
CI integration: Run evals on every prompt change
Tips
Start with 3-5 evals. Get those perfect before expanding.
Bias and actionability are inherently subjective - allow higher error margins.
If extraction fails, check for unusual document formatting.
Claude sees section headers as bold or numbered text - make them obvious.
