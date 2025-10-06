"""
Questionnaire Scoring Agent
Extracts questions from documents and scores them on multiple attributes.
"""

import anthropic
import base64
import csv
import io
import json
import os
import time
from pathlib import Path
from typing import Dict, List
from docx import Document
from dotenv import load_dotenv, find_dotenv
# from galileo import GalileoLogger  # Commented out due to Python 3.13 compatibility issues

# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Galileo configuration
GALILEO_API_KEY = os.getenv("GALILEO_API_KEY")
GALILEO_PROJECT = os.getenv("GALILEO_PROJECT", "survey-eval")
GALILEO_LOG_STREAM = os.getenv("GALILEO_LOG_STREAM", "questionnaire-scoring")

# Mock Galileo logger for Python 3.13 compatibility
class MockGalileoLogger:
    def addLLMSpan(self, **kwargs):
        print(f"[GALILEO] LLM Span: {kwargs.get('name', 'Unknown')}")
    
    def addWorkflowSpan(self, **kwargs):
        print(f"[GALILEO] Workflow Span: {kwargs.get('name', 'Unknown')}")

# Initialize logger (mock for now)
galileo_logger = MockGalileoLogger()

SCORING_PROMPT = """You are a questionnaire scoring agent. Your task:

1. **Parse the input document**
   - Extract all questions
   - Identify section headers (look for bold text, numbering like "Section 1:", or headers)
   - If a section is not found, use "General" as the section name
   - Give each question a number that includes it's order and some part of the section name
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
    
    - Narrative Value: How valuable is the question to the target story?
     * 5 = Essential to the story
     * 3 = Somewhat useful for the story
     * 1 = Completely irrelevant to the story

    - Research Value: How valuable is this information to our product or marketing research?
     * 5 = Essential to the research
     * 3 = Somewhat useful for the research
     * 1 = Completely irrelevant to the research

     - Pivot Value: Is this question likely to be one that creates useful segments of the target audience?
     * 5 = Yes a core pivot question
     * 3 = Would be a pivot for a smaller segment of the target audience
     * 1 = Not a pivot question



3. **Output ONLY a CSV** with these exact columns:
   Section,Question_Number,Question_Text,Clarity,Specificity,Bias,Actionability,Narrative_Value,Research_Value,Pivot_Value

**Rules**:
- If no section is found, use "General" as the section name
- Number questions sequentially within each section throughout the document
- Pay attention to branching logic and update those numbers as you go
- Include the question choices with the question text
- Do NOT include section averages in the CSV (we'll calculate those separately)
- Question_Text should be the exact text from the document
- All scores must be integers 1-5
- Output ONLY the CSV, no other text or markdown formatting

**Example output format**:
Section,Question_Number,Question_Text,Clarity,Specificity,Bias,Actionability,Narrative_Value,Research_Value,Pivot_Value
Demographics,1,What is your age?,5,5,5,3,5,5,5
Demographics,2,How satisfied are you with our amazing product?,4,2,2,3,3,3,3
"""


class QuestionnaireScorer:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def score_document(self, doc_path: str, save_csv: bool = True) -> Dict:
        """
        Score a questionnaire document.
        
        Args:
            doc_path: Path to DOCX or PDF file
            save_csv: Whether to save the raw CSV output to a file
            
        Returns:
            Dict with 'questions' list and 'section_averages' dict
        """
        # Start workflow span
        galileo_logger.addWorkflowSpan(
            input={"document_path": doc_path, "save_csv": save_csv},
            output="",  # Will be updated at the end
            name="Document Scoring Workflow",
            metadata={"document_path": doc_path, "save_csv": save_csv}
        )
        suffix = Path(doc_path).suffix.lower()
        
        # Handle DOCX - extract text first
        if suffix == ".docx":
            text_content = self._extract_docx_text(doc_path)
            content_blocks = [
                {"type": "text", "text": f"Here is the questionnaire document:\n\n{text_content}\n\n{SCORING_PROMPT}"}
            ]
        
        # Handle PDF - send as document
        elif suffix == ".pdf":
            with open(doc_path, "rb") as f:
                doc_data = base64.b64encode(f.read()).decode()
            
            content_blocks = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": doc_data
                    }
                },
                {"type": "text", "text": SCORING_PROMPT}
            ]
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .docx or .pdf")
        
        # Call Claude with Galileo logging
        start_time = time.time()
        
        # Log the LLM call to Galileo
        galileo_logger.addLLMSpan(
            input=SCORING_PROMPT,
            output="",  # Will be updated after response
            name="Questionnaire Scoring",
            model="claude-sonnet-4-20250514",
            temperature=0.0,
            max_tokens=4000,
            metadata={
                "document_path": doc_path,
                "file_type": suffix,
                "prompt_type": "questionnaire_scoring"
            }
        )
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": content_blocks
            }]
        )
        
        # Update the span with the actual response
        duration_ns = int((time.time() - start_time) * 1_000_000_000)
        galileo_logger.addLLMSpan(
            input=SCORING_PROMPT,
            output=response.content[0].text,
            name="Questionnaire Scoring",
            model="claude-sonnet-4-20250514",
            temperature=0.0,
            max_tokens=4000,
            durationNs=duration_ns,
            metadata={
                "document_path": doc_path,
                "file_type": suffix,
                "prompt_type": "questionnaire_scoring",
                "response_length": len(response.content[0].text)
            }
        )
        
        # Parse CSV response
        csv_text = response.content[0].text
        csv_text = csv_text.strip()
        
        # Remove markdown formatting if present
        if csv_text.startswith("```"):
            lines = csv_text.split("\n")
            csv_text = "\n".join(lines[1:-1]) if len(lines) > 2 else csv_text
        
        # Save raw CSV if requested
        if save_csv:
            csv_filename = f"scoring_results_{Path(doc_path).stem}.csv"
            with open(csv_filename, "w", encoding="utf-8") as f:
                f.write(csv_text)
            print(f"Raw CSV saved to: {csv_filename}")
        
        result = self._parse_csv_output(csv_text)
        
        # Complete workflow span
        galileo_logger.addWorkflowSpan(
            input={"document_path": doc_path, "save_csv": save_csv},
            output=result,
            name="Document Scoring Workflow",
            metadata={
                "document_path": doc_path,
                "save_csv": save_csv,
                "questions_found": len(result["questions"]),
                "sections_found": len(result["section_averages"]),
                "sections": list(result["section_averages"].keys())
            }
        )
        
        return result
    
    def _extract_docx_text(self, doc_path: str) -> str:
        """Extract text from DOCX file, preserving structure."""
        doc = Document(doc_path)
        text_parts = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Check if it looks like a heading (bold or specific style)
                if para.style.name.startswith('Heading'):
                    text_parts.append(f"\n## {text}\n")
                else:
                    text_parts.append(text)
        
        return "\n".join(text_parts)
    
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
    
    def save_csv(self, csv_text: str, output_path: str):
        """Save raw CSV text to file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(csv_text)
        print(f"CSV saved to: {output_path}")


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
    
    # Note about CSV file
    csv_filename = f"scoring_results_{Path(sys.argv[1]).stem}.csv"
    print(f"Raw CSV data saved to {csv_filename}")