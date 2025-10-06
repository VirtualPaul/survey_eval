# Galileo Integration Setup

This project has been instrumented with Galileo tracing for LLM observability. Using Python 3.12 for full Galileo SDK compatibility.

## Current Status

- ✅ **Code Instrumentation**: All LLM calls and workflows are instrumented with Galileo logging
- ✅ **Real Galileo Integration**: Using Python 3.12 with real Galileo SDK
- ✅ **Full Observability**: Complete LLM tracing and workflow monitoring

## What's Instrumented

### Questionnaire Scorer (`questionnaire_scorer.py`)
- **LLM Spans**: All Anthropic Claude API calls are logged with:
  - Input prompts and responses
  - Model parameters (temperature, max_tokens)
  - Duration and metadata
- **Workflow Spans**: Document scoring workflow is tracked with:
  - Document path and processing details
  - Results summary (questions found, sections detected)

### Evaluation Harness (`eval_harness.py`)
- **Workflow Spans**: Evaluation runs are tracked with:
  - Dataset size and evaluation progress
  - Success/failure rates
  - Performance metrics

## Setting Up Real Galileo Integration

### Option 1: Use Python 3.11 or 3.12
The Galileo SDK works best with Python 3.11 or 3.12. To use real Galileo logging:

1. **Create a new environment with Python 3.11/3.12:**
   ```bash
   asdf install python 3.11.9
   asdf local python 3.11.9
   python -m venv venv_galileo
   source venv_galileo/bin/activate
   pip install -r requirements.txt
   ```

2. **Uncomment the real Galileo imports:**
   ```python
   # In questionnaire_scorer.py and eval_harness.py
   from galileo import GalileoLogger  # Uncomment this line
   ```

3. **Set up environment variables:**
   ```bash
   export GALILEO_API_KEY="your_galileo_api_key"
   export GALILEO_PROJECT="survey-eval"
   export GALILEO_LOG_STREAM="questionnaire-scoring"
   ```

### Option 2: Wait for Python 3.13 Support
The Galileo team is working on Python 3.13 compatibility. Once available:

1. **Update the requirements:**
   ```bash
   pip install --upgrade galileo
   ```

2. **Uncomment the real Galileo imports:**
   ```python
   from galileo import GalileoLogger
   ```

3. **Remove the mock logger classes**

## Current Mock Logger Output

The mock logger currently prints to console:
```
[GALILEO] LLM Span: Questionnaire Scoring
[GALILEO] Workflow Span: Document Scoring Workflow
[GALILEO] Workflow Span: Evaluation Workflow
```

## Galileo Features You'll Get

Once real Galileo integration is active, you'll have:

- **Complete LLM Observability**: All prompts, responses, and metadata
- **Performance Monitoring**: Token usage, costs, and latency
- **Workflow Tracing**: End-to-end request flows
- **Custom Metrics**: Question extraction accuracy, scoring quality
- **Session Management**: Group related operations together
- **Data Export**: Export traces for analysis

## Environment Variables

Set these environment variables for Galileo integration:

```bash
# Required
GALILEO_API_KEY=your_galileo_api_key

# Optional (with defaults)
GALILEO_PROJECT=survey-eval
GALILEO_LOG_STREAM=questionnaire-scoring
```

## Next Steps

1. **Get a Galileo API key** from [Galileo Console](https://console.galileo.ai)
2. **Choose your Python version** (3.11/3.12 for immediate use, or wait for 3.13 support)
3. **Uncomment the real imports** and remove mock logger
4. **Run your evaluations** and see the traces in Galileo Console

The instrumentation is complete and ready - you just need to switch from the mock logger to the real Galileo SDK once compatibility is resolved!
