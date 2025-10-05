"""
Evaluation harness for questionnaire scoring agent.
"""

import json
import pandas as pd
from typing import Dict, List
from questionnaire_scorer import QuestionnaireScorer


THRESHOLDS = {
    "extraction_accuracy": 0.95,
    "clarity_mae": 0.5,
    "specificity_mae": 0.5,
    "bias_mae": 0.7,
    "actionability_mae": 0.8,
    "clarity_within_1": 0.85,
    "specificity_within_1": 0.85,
    "bias_within_1": 0.80,
    "actionability_within_1": 0.80,
}


def calculate_eval_metrics(predicted: Dict, expected: Dict) -> Dict:
    """Compare agent output to ground truth."""
    metrics = {
        "extraction_accuracy": 0.0,
        "score_mae": {},
        "score_within_1": {},
        "section_detection": 0.0,
    }
    
    # Question extraction accuracy
    pred_questions = {q["question_text"].strip().lower() for q in predicted["questions"]}
    exp_questions = {q["question_text"].strip().lower() for q in expected["questions"]}
    
    if len(exp_questions) > 0:
        metrics["extraction_accuracy"] = len(pred_questions & exp_questions) / len(exp_questions)
    
    # Scoring accuracy for matched questions
    attributes = ["clarity", "specificity", "bias", "actionability"]
    
    for attr in attributes:
        errors = []
        within_1 = []
        
        for exp_q in expected["questions"]:
            exp_text = exp_q["question_text"].strip().lower()
            
            # Find matching predicted question
            pred_q = next(
                (q for q in predicted["questions"] 
                 if q["question_text"].strip().lower() == exp_text),
                None
            )
            
            if pred_q:
                error = abs(pred_q[attr] - exp_q[attr])
                errors.append(error)
                within_1.append(error <= 1)
        
        metrics["score_mae"][attr] = sum(errors) / len(errors) if errors else 0.0
        metrics["score_within_1"][attr] = sum(within_1) / len(within_1) if within_1 else 0.0
    
    # Section detection
    if expected.get("section_averages"):
        pred_sections = set(predicted["section_averages"].keys())
        exp_sections = set(expected["section_averages"].keys())
        if len(exp_sections) > 0:
            metrics["section_detection"] = len(pred_sections & exp_sections) / len(exp_sections)
    
    return metrics


class EvalHarness:
    def __init__(self, eval_dataset_path: str):
        self.eval_dataset = json.load(open(eval_dataset_path))
        self.scorer = QuestionnaireScorer()
    
    def run_evals(self) -> pd.DataFrame:
        """Run agent on all eval cases."""
        results = []
        
        for eval_case in self.eval_dataset:
            eval_id = eval_case["id"]
            print(f"\n{'='*60}")
            print(f"Running eval: {eval_id}")
            print(f"{'='*60}")
            
            try:
                # Get agent prediction
                predicted = self.scorer.score_document(eval_case["document"])
                expected = eval_case["expected_output"]
                
                # Calculate metrics
                metrics = calculate_eval_metrics(predicted, expected)
                
                # Flatten for DataFrame
                result = {
                    "eval_id": eval_id,
                    "extraction_acc": metrics["extraction_accuracy"],
                    "section_detection": metrics["section_detection"],
                }
                
                # Add MAE metrics
                for attr, mae in metrics["score_mae"].items():
                    result[f"{attr}_mae"] = mae
                
                # Add within_1 metrics
                for attr, within_1 in metrics["score_within_1"].items():
                    result[f"{attr}_within_1"] = within_1
                
                results.append(result)
                
                # Print summary
                print(f"\nExtraction Accuracy: {metrics['extraction_accuracy']:.1%}")
                print(f"Section Detection: {metrics['section_detection']:.1%}")
                print("\nScoring MAE:")
                for attr, mae in metrics["score_mae"].items():
                    print(f"  {attr}: {mae:.2f}")
                
            except Exception as e:
                print(f"❌ ERROR in {eval_id}: {e}")
                results.append({
                    "eval_id": eval_id,
                    "error": str(e)
                })
        
        return pd.DataFrame(results)
    
    def check_pass_fail(self, results_df: pd.DataFrame) -> bool:
        """Check if evals pass defined thresholds."""
        print(f"\n{'='*60}")
        print("EVAL RESULTS SUMMARY")
        print(f"{'='*60}\n")
        
        # Show aggregate metrics
        numeric_cols = results_df.select_dtypes(include=['float64', 'int64']).columns
        means = results_df[numeric_cols].mean()
        
        print("Average Metrics:")
        for col, val in means.items():
            print(f"  {col}: {val:.3f}")
        
        print(f"\n{'='*60}")
        print("THRESHOLD CHECKS")
        print(f"{'='*60}\n")
        
        all_passed = True
        
        for metric, threshold in THRESHOLDS.items():
            if metric not in means:
                continue
                
            actual = means[metric]
            
            # MAE metrics: lower is better
            if metric.endswith("_mae"):
                passed = actual <= threshold
                symbol = "✅" if passed else "❌"
                print(f"{symbol} {metric}: {actual:.3f} (threshold: ≤{threshold})")
            # Other metrics: higher is better
            else:
                passed = actual >= threshold
                symbol = "✅" if passed else "❌"
                print(f"{symbol} {metric}: {actual:.3f} (threshold: ≥{threshold})")
            
            if not passed:
                all_passed = False
        
        print(f"\n{'='*60}")
        if all_passed:
            print("🎉 ALL EVALS PASSED!")
        else:
            print("⚠️  SOME EVALS FAILED - SEE ABOVE")
        print(f"{'='*60}\n")
        
        return all_passed


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python eval_harness.py <path_to_eval_dataset.json>")
        sys.exit(1)
    
    harness = EvalHarness(sys.argv[1])
    results_df = harness.run_evals()
    
    # Save results
    results_df.to_csv("eval_results.csv", index=False)
    print(f"\nDetailed results saved to eval_results.csv")
    
    # Check pass/fail
    passed = harness.check_pass_fail(results_df)
    
    sys.exit(0 if passed else 1)