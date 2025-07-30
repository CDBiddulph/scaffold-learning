# Human Preference Domain Implementation

## Overview
Implement a domain that uses the LMarena Arena Human Preference 55k dataset. The LLM sees a prompt and two responses (A and B), and must predict which one was preferred by humans. Scoring is binary: 1.0 if correct, 0.0 if incorrect.

## Key Implementation Details

### Answer Extraction Refactoring
- Create `src/scaffold_learning/domains/answer_extraction.py` with `extract_answer_letter()` function
- This will be shared between MCQ and human-preference domains
- MCQ will be refactored to use this shared utility
- The function accepts a `valid_letters` parameter to restrict which letters are valid (e.g., "AB" for preference, "ABCDE" for MCQ)

### Dataset Structure
- Uses the lmarena-ai/arena-human-preference-55k dataset from HuggingFace
- Filter criteria:
  - Only single prompt strings (skip entries where prompt is a list/array)
  - Only clear preferences (skip ties where winner_tie=1)
  - Use existing IDs from the dataset if available
- Scoring data: `{"correct_answer": "A"}` or `{"correct_answer": "B"}`

### Input Prompt Format
```
Original prompt: [prompt text]

Response A:
[response_a content]

Response B:
[response_b content]

Which response was preferred? Write "Answer: A" or "Answer: B".
```

### File Structure
```
src/scaffold_learning/
├── domains/
│   ├── answer_extraction.py  # NEW: Shared answer extraction utility
│   ├── human_preference/     # NEW: Human preference domain
│   │   ├── __init__.py
│   │   ├── prepare_datasets.py
│   │   ├── score.py
│   │   └── data/            # Empty until prepare_datasets is run
│   └── mcq/
│       └── score.py         # MODIFIED: Use shared answer extraction
└── core/
    └── scoring_utils.py     # MODIFIED: Add human-preference domain
```

### Implementation Steps

1. **Create shared answer extraction utility**
   - Extract patterns from MCQ score.py
   - Generalize to support configurable valid letters
   - Include comprehensive regex patterns for various answer formats

2. **Refactor MCQ to use shared utility**
   - Import from domains.answer_extraction
   - Ensure all tests still pass

3. **Implement human-preference dataset preparation**
   - Download from HuggingFace using HF_TOKEN
   - Filter for single prompts and non-ties
   - Convert winner_model_a/b flags to "A"/"B" preference
   - Create input prompts with the specified format
   - Save using dataset_utils.save_dataset_splits

4. **Implement scoring logic**
   - Use extract_answer_letter with valid_letters="AB"
   - Binary scoring: 1.0 if correct, 0.0 otherwise
   - Handle command-line interface similar to MCQ

5. **Register domain in scoring utils**
   - Add "human-preference" case to create_scoring_function
   - Add path for get_scoring_function_code

### API Compatibility
- Uses same HF_TOKEN environment variable as MCQ
- Command-line arguments follow same pattern as MCQ/crosswords prepare_datasets
- Scoring function signature matches existing domains

### Testing Strategy
- Test answer extraction with A/B specific patterns
- Test dataset filtering logic
- Test scoring with various response formats
- Ensure backward compatibility for MCQ after refactoring

### Dataset Preparation Command
```bash
python -m src.scaffold_learning.domains.human_preference.prepare_datasets \
    --num-train 1000 \
    --num-valid 200 \
    --num-test 200 \
    output_dir
```

### Scoring Command
```bash
python -m src.scaffold_learning.domains.human_preference.score \
    expected.jsonl \
    attempted_response.txt \
    --question example_id
```