"""
Questionnaire Scoring Agent
Extracts questions from documents and scores them on multiple attributes.
"""

import anthropic
import base64
import csv
import io
import json
from pathlib import Path
from typing import Dict, List
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


SCORING_PROMPT = """You are a questionnaire scoring agent. Your task:

1. **Parse the input document**
   - Extract all questions
   - Identify section headers (look for bold text, numbering like "Section 1:", or headers)
   - Preserve question order

2. **Score each question** on these attributes (1-5 scale):
   - Clarity: Is the question unambiguous and easy to understand?
     * 5 = Crystal clear, no room for misinterpretation
     * 3 = Somewhat clear but could be improved
     * 1 = Confusing or vague
   
   - Specificity: Does it ask for concrete, specific information?
     * 5 = Very specific, narrow scope
     * 3 = Moderately specific
     * 1 = Extremely broad or general
   
   - Bias: Is the question neutrally worded?
     * 5 = Completely neutral
     * 3 = Slightly leading or contains mild bias
     * 1 = Heavily biased or leading
   
   - Actionability: Can responses drive concrete decisions?
     * 5 = Directly actionable insights
     * 3 = Somewhat useful for decisions
     * 1 = Not actionable

3. **Output ONLY a CSV** with these exact columns:
   Section,Question_Number,Question_Text,Clarity,Specificity,Bias,Actionability

**Rules**:
- If no section is found, use "General" as the section name
- Number questions sequentially within each section
- Do NOT include section averages in the CSV (we'll calculate those separately)
- Question_Text should be the exact text from the document
- All scores must be integers 1-5
- Output ONLY the CSV, no other text or markdown formatting

**Example output format**:
Section,Question_Number,Question_Text,Clarity,Specificity,Bias,Actionability
Demographics,1,What is your age?,5,5,5,3
Demographics,2,How satisfied are you with our amazing product?,4,2,2,3
"""


class QuestionnaireScorer:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    def score_document(self, doc_path: str) -> Dict:
        """
        Score a questionnaire document.
        
        Args:
            doc_path: Path to DOCX or PDF file
            
        Returns:
            Dict with 'questions' list and 'section_averages' dict
        """
        # Read and encode document
        with open(doc_path, "rb") as f:
            doc_data = base64.b64encode(f.read()).decode()
        
        # Determine media type
        suffix = Path(doc_path).suffix.lower()
        media_types = {
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
            ".doc": "application/msword"
        }
        media_type = media_types.get(suffix, "application/pdf")
        
        # Call Claude
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": doc_data
                        }
                    },
                    {"type": "text", "text": SCORING_PROMPT}
                ]
            }]
        )
        
        # Parse CSV response
        csv_text = response.content[0].text
        csv_text = csv_text.strip()
        
        # Remove markdown formatting if present
        if csv_text.startswith("```"):
            lines = csv_text.split("\n")
            csv_text = "\n".join(lines[1:-1]) if len(lines) > 2 else csv_text
        
        return self._parse_csv_output(csv_text)
    
    def _parse_csv_output(self, csv_text: str) -> Dict:
        """Parse CSV string into structured format with section averages."""
        reader = csv.DictReader(io.StringIO(csv_text))
        questions = []
        section_scores = {}
        
        for row in reader:
            question = {
                "section": row["Section"],
                "question_number": int(row["Question_Number"]),
                "question_text": row["Question_Text"],
                "clarity": int(row["Clarity"]),
                "specificity": int(row["Specificity"]),
                "bias": int(row["Bias"]),
                "actionability": int(row["Actionability"])
            }
            questions.append(question)
            
            # Collect scores by section
            section = row["Section"]
            if section not in section_scores:
                section_scores[section] = {
                    "clarity": [],
                    "specificity": [],
                    "bias": [],
                    "actionability": []
                }
            
            section_scores[section]["clarity"].append(int(row["Clarity"]))
            section_scores[section]["specificity"].append(int(row["Specificity"]))
            section_scores[section]["bias"].append(int(row["Bias"]))
            section_scores[section]["actionability"].append(int(row["Actionability"]))
        
        # Calculate averages
        section_averages = {}
        for section, scores in section_scores.items():
            section_averages[section] = {
                attr: sum(vals) / len(vals)
                for attr, vals in scores.items()
            }
        
        return {
            "questions": questions,
            "section_averages": section_averages
        }
    
    def save_results(self, results: Dict, output_path: str):
        """Save results to JSON file."""
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python questionnaire_scorer.py <path_to_document>")
        sys.exit(1)
    
    scorer = QuestionnaireScorer()
    results = scorer.score_document(sys.argv[1])
    
    print("\n=== SCORING RESULTS ===\n")
    print(f"Found {len(results['questions'])} questions")
    print(f"Sections: {', '.join(results['section_averages'].keys())}\n")
    
    print("Section Averages:")
    for section, averages in results["section_averages"].items():
        print(f"\n{section}:")
        for attr, score in averages.items():
            print(f"  {attr}: {score:.2f}")
    
    # Save to file
    output_path = "scoring_results.json"
    scorer.save_results(results, output_path)
    print(f"\nFull results saved to {output_path}")