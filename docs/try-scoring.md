# Try Scoring Implementation Plan

## Overview
Create a CLI script that allows users to iteratively test scoring functions on domain examples by editing inputs in vim and seeing scores immediately.

## Files to Create/Modify

### New File: `src/scaffold_learning/cli/try_scoring.py`
**Estimated lines:** ~150-200

#### Public Functions:

##### `main()`
```python
def main() -> None:
    """Entry point for the try-scoring CLI tool.
    
    Parses command line arguments and runs the interactive scoring loop.
    
    Raises:
        ValueError: If domain is not recognized or example ID not found
    """
```
- Called by: Script entry point
- Uses argparse to parse: jsonl_path, example_id, --domain, --domain-param

##### `load_example(jsonl_path: str, example_id: str) -> dict`
```python
def load_example(jsonl_path: str, example_id: str) -> dict:
    """Load a specific example from a JSONL file.
    
    Args:
        jsonl_path: Path to the JSONL file
        example_id: ID of the example to load
        
    Returns:
        The example dict from the JSONL file
        
    Raises:
        ValueError: If example_id not found in file
    """
```
- Called by: `main()`

##### `format_prompt(example: dict) -> str`
```python
def format_prompt(example: dict) -> str:
    """Format the example data into a readable prompt.
    
    Shows field names and values in a readable format.
    Flattens nested fields using dot notation (e.g., scoring_data.solution).
    
    Args:
        example: The example dict loaded from JSONL
        
    Returns:
        Formatted string with fields and separator line
    """
```
- Called by: `run_scoring_loop()`

##### `run_scoring_loop(example: dict, domain: str, domain_param: Optional[str]) -> None`
```python
def run_scoring_loop(example: dict, domain: str, domain_param: Optional[str]) -> None:
    """Run the interactive vim editing and scoring loop.
    
    Opens vim with the formatted prompt, gets user input, scores it,
    displays results, and asks whether to continue.
    
    Args:
        example: The example dict loaded from JSONL
        domain: Domain name (e.g., 'crosswords')
        domain_param: Optional domain parameter (e.g., 'lenient')
    """
```
- Called by: `main()`

##### `edit_in_vim(content: str) -> str`
```python
def edit_in_vim(content: str) -> str:
    """Open vim with the given content and return the edited result.
    
    Args:
        content: Initial content for the vim buffer
        
    Returns:
        The edited content after user saves and exits vim
    """
```
- Called by: `run_scoring_loop()`

##### `extract_answer(content: str) -> str`
```python
def extract_answer(content: str) -> str:
    """Extract the answer portion from the vim buffer content.
    
    Finds the separator line and returns everything below it, stripped.
    
    Args:
        content: Full vim buffer content
        
    Returns:
        The user's answer (text below separator line)
    """
```
- Called by: `run_scoring_loop()`

##### `score_answer(example: dict, answer: str, domain: str, domain_param: Optional[str]) -> str`
```python
def score_answer(example: dict, answer: str, domain: str, domain_param: Optional[str]) -> str:
    """Score the user's answer using the domain's scoring function.
    
    Args:
        example: The example dict with expected answer
        answer: The user's attempted answer
        domain: Domain name
        domain_param: Optional domain parameter
        
    Returns:
        The score as a string
    """
```
- Called by: `run_scoring_loop()`

### New File: `try-scoring` (shell script in project root)
**Estimated lines:** ~5
- Simple shell script that calls `python -m src.scaffold_learning.cli.try_scoring`

## External Libraries/Frameworks
- `tempfile` for creating temporary files for vim
- `subprocess` for calling vim
- `json` for parsing JSONL files
- `argparse` for CLI argument parsing

## Existing Code to Reuse

### From `src/scaffold_learning/domains/crosswords/score.py`:
- Will reuse `score()` function
- Called by: `score_answer()`
- Can use as-is, passing mode parameter if domain_param is provided

### From other domains:
- Need to identify scoring functions in other domains (if they exist)
- Will import and call them similarly to crosswords

## Tests to Create

### File: `tests/cli/test_try_scoring.py`

#### Unit Tests:
1. `test_load_example_success` - Test loading valid example from JSONL
2. `test_load_example_missing_id` - Test error when ID doesn't exist
3. `test_format_prompt_simple` - Test formatting with simple fields
4. `test_format_prompt_nested` - Test formatting with nested fields (scoring_data.solution)
5. `test_extract_answer` - Test extracting answer below separator line
6. `test_extract_answer_with_whitespace` - Test whitespace stripping

## Implementation Milestones

### Milestone 1: Core data loading and formatting
1. Write tests for `load_example` and `format_prompt`
2. Implement `load_example` function to read JSONL and find example by ID
3. Implement `format_prompt` to create readable display with separator line

### Milestone 2: Vim integration
1. Write tests for `extract_answer`
2. Implement `edit_in_vim` using tempfile and subprocess
3. Implement `extract_answer` to parse vim buffer content

### Milestone 3: Scoring integration
1. Implement `score_answer` to call domain-specific scoring functions
2. Handle domain parameter passing (e.g., lenient mode for crosswords)

### Milestone 4: Interactive loop
1. Implement `run_scoring_loop` with vim editing, scoring, and continue/quit prompt
2. Implement `main()` with argument parsing
3. Create shell script for easy execution

## Additional Implementation Details

### Separator Line
The separator line will be:
```
=== SUBMIT YOUR ANSWER BELOW THIS LINE ===
```

### Interactive Prompt
After showing score, display:
```
Answer: [user's answer]
Score: [score result]

Press Enter to continue editing, or 'q' to quit: 
```

### Domain Support
Initially support crosswords domain. Structure the code to easily add other domains by importing their scoring functions dynamically based on the --domain flag.

### Temp File Handling
Use `tempfile.NamedTemporaryFile` with delete=False to ensure the file persists between vim sessions within the same run.

## Questions Answered During Planning

- Script name: `try-scoring.py`
- Preserve user input between iterations: Yes
- Show formatted prompt with field names and values
- No syntax highlighting needed in vim
- Show both answer and score after each iteration
- No need for explicit ID validation (will fail naturally)
- All answers should be strings for scoring