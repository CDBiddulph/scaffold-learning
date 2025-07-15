# Documentation for Unified Make and Run CLI Implementation

## Overview
This document contains all information needed to implement the unified `scaffold` CLI that replaces `evaluate_baseline.py`, `generate_scaffold.py`, and `run_scaffold.py` with a single command supporting `make` and `run` subcommands.

## Background and Motivation
The current three CLI scripts have overlapping functionality with different interfaces and inconsistent data organization. The unified CLI will:
- Eliminate duplicate code and interfaces
- Create consistent data organization with scaffold-local logging
- Support combined make+run workflows
- Maintain clean separation between experiments/ and scaffolds/ directories
- Support three scaffold generation modes: baseline, generated from examples, and generated from task

## CLI Interface Specification

### Command Structure
```bash
scaffold make [options]                    # Generate scaffold only
scaffold run [options]                     # Run existing scaffold  
scaffold make run [options]                # Generate and run scaffold
```

### Arguments by Subcommand

**Make arguments:**
- `--name` (required): Scaffold name
- Generation mode (exactly one required):
  - `--baseline` with `--data-dir`: Create prompt-only baseline
  - `--data-dir` with `--scaffolder-model`: Generate scaffold from examples
  - `--task` with `--scaffolder-model`: Generate scaffold from task description
- `--num-train-examples` (required): Training examples to use
- `--train-seed` (int): Random seed for training example sampling
- `--show-scoring-function` (flag): Include scoring function in prompt (baseline/examples only)
- `--suggest-hack` (flag): Include hack encouragement text

**Run arguments:**
- `--base-dir` (required if no preceding make): Base directory to find scaffold
- `--name` (required if no preceding make): Scaffold name to run
- `--executor-model` (required): Model for scaffold execution
- Input (exactly one required):
  - `--input`: Input string
  - `--file`: Path to input file  
  - `--data-dir` with `--num-test-examples`: Dataset evaluation
- `--num-test-examples` (required with data-dir): Number of test examples
- `--test-seed` (int): Random seed for test example sampling
- `--domain` (required with data-dir): Domain for scoring function
- `--timeout` (default None): Execution timeout in seconds
- `--no-build` (flag): Skip Docker image build
- `--thinking-budget` (default 0): Thinking budget tokens

### Argument Validation Rules
1. **Generation modes**: Exactly one of the three generation modes required for make
2. **Model requirements**: 
   - `--scaffolder-model` required for non-baseline generation
   - `--scaffolder-model` forbidden with `--baseline`
   - `--executor-model` required for run
3. **Domain requirement**: Only required when evaluation will happen (with `--data-dir` in run)
4. **Seeds**: 
   - `--train-seed` only valid when using `--data-dir` for make
   - `--test-seed` only valid when using `--data-dir` for run
5. **Unused argument errors**: Throw error if any argument provided won't be used

## Directory Structure

### Output Organization
```
scaffolds/
├── generated/           # Generated scaffolds (non-baseline)
│   └── {name}/
│       ├── scaffold.py
│       ├── llm_interfaces.py
│       ├── metadata.xml
│       └── runs/        # Created on first run
│           └── eval_{timestamp}/
│               ├── 0.log
│               ├── 1.log (if multi-example)
│               └── results.json
└── baselines/           # Baseline scaffolds
    └── {name}/
        ├── scaffold.py
        ├── llm_interfaces.py
        ├── metadata.xml
        └── runs/        # Created on first run
            └── eval_{timestamp}/
                ├── 0.log
                └── results.json

experiments/             # Existing experiment structure (unchanged)
├── {experiment}_{timestamp}/
│   ├── scaffolds/
│   │   └── {scaffold_id}/
│   │       ├── scaffold.py
│   │       ├── metadata.xml
│   │       └── runs/    # NEW: Created when run via unified CLI
│   │           └── eval_{timestamp}/
│   │               ├── 0.log
│   │               └── results.json
│   └── logs/           # Existing experiment logs (separate system)
```

### Base Directory Inference
- **Make mode**: Automatically infer base directory
  - `--baseline` → `scaffolds/baselines/`
  - No `--baseline` → `scaffolds/generated/`
- **Run-only mode**: Require explicit `--base-dir` argument

## Implementation Details

### Files to Create/Modify

**New file: `src/scaffold_learning/cli/make_and_run.py`**
- Main CLI implementation with subcommand parsing
- All scaffold creation and running logic
- Approximately 500 lines

**Modified file: `pyproject.toml`**
- Remove old console_scripts entries: `generate-scaffold`, `run-scaffold`, `evaluate-baseline`
- Add new entry: `scaffold = "scaffold_learning.cli.make_and_run:main"`

**Files to delete (after implementation):**
- `src/scaffold_learning/cli/evaluate_baseline.py`
- `src/scaffold_learning/cli/generate_scaffold.py`
- `src/scaffold_learning/cli/run_scaffold.py`

### Core Functions

**`ScaffoldConfig` (dataclass)**
```python
@dataclass
class ScaffoldConfig:
    # Subcommand flags
    do_make: bool
    do_run: bool
    
    # Make arguments
    name: Optional[str]
    scaffolder_model: Optional[str]
    task: Optional[str]
    baseline: bool
    data_dir: Optional[Path]
    num_train_examples: Optional[int]
    train_seed: Optional[int]
    show_scoring_function: bool
    suggest_hack: bool
    
    # Run arguments
    base_dir: Optional[Path]
    executor_model: Optional[str]
    input_string: Optional[str]
    input_file: Optional[Path]
    num_test_examples: Optional[int]
    test_seed: Optional[int]
    domain: Optional[str]
    timeout: Optional[int]
    no_build: bool
    thinking_budget: int
```

**Key function signatures:**
```python
def parse_args() -> ScaffoldConfig  # Public for testing
def _validate_arguments(config: ScaffoldConfig) -> None
def _infer_base_dir(config: ScaffoldConfig) -> Path
def _make_scaffold(config: ScaffoldConfig) -> Path
def _run_scaffold(config: ScaffoldConfig, scaffold_dir: Optional[Path] = None) -> Dict[str, Any]
def _setup_run_directory(scaffold_dir: Path) -> Path
def _resolve_scaffold_directory(config: ScaffoldConfig) -> Path
def _get_input_string(config: ScaffoldConfig) -> Optional[str]
def _load_test_examples(config: ScaffoldConfig) -> Optional[List[DatasetExample]]
def main() -> None
```

### Scaffold Generation Modes

**1. Baseline from examples:**
```python
# Uses make_prompt_only_scaffold()
# Config: baseline=True, data_dir=Path, num_train_examples=int
# No scaffolder_model needed
```

**2. Generated from examples:**
```python
# Uses generate_scaffold() with examples parameter
# Config: data_dir=Path, scaffolder_model=str, num_train_examples=int
# Creates scaffold using LLM to analyze training examples
```

**3. Generated from task:**
```python
# Uses generate_scaffold() with task_description parameter
# Config: task=str, scaffolder_model=str
# Creates scaffold using LLM to interpret task description
```

### Code Reuse Strategy

**From `generate_scaffold.py`:**
- LLM factory usage for scaffolder creation
- `generate_scaffold()` calling for both task and examples modes
- Directory creation and scaffold saving logic

**From `evaluate_baseline.py`:**
- Dataset loading with train/test split
- Example sampling with seeds
- `make_prompt_only_scaffold()` for baseline creation
- Evaluation loop with scoring
- Results saving

**From `run_scaffold.py`:**
- Input handling (file vs string)
- Docker build management
- Single execution logic
- Timeout handling

### Error Handling Strategy
- Let errors bubble up naturally (don't catch exceptions)
- Validate arguments early with clear error messages
- Use type hints and dataclasses for validation
- Follow existing pattern of not adding explicit existence checks

### Testing Strategy

**Unit tests (`tests/cli/test_make_and_run.py`):**
1. **Argument parsing tests:**
   - `test_parse_args_make_baseline()`
   - `test_parse_args_make_from_examples()`
   - `test_parse_args_make_from_task()`
   - `test_parse_args_run_only()`
   - `test_parse_args_make_run_combined()`

2. **Validation tests:**
   - `test_validate_baseline_requires_data_dir()`
   - `test_validate_scaffolder_model_forbidden_with_baseline()`
   - `test_validate_domain_required_only_for_evaluation()`
   - `test_validate_seeds_only_with_data_dir()`
   - `test_validate_exactly_one_generation_mode()`

3. **Helper function tests:**
   - `test_infer_base_dir_baseline()`
   - `test_infer_base_dir_generated()`
   - `test_resolve_scaffold_directory()`
   - `test_setup_run_directory()`
   - `test_get_input_string_variations()`

**Integration tests:**
- `test_make_run_baseline_workflow()` - Full baseline creation and evaluation
- `test_make_run_from_examples_workflow()` - Generated from examples and evaluation
- `test_make_from_task_workflow()` - Generated from task (no evaluation)
- `test_run_existing_scaffold_with_eval()` - Run existing scaffold with test data
- `test_run_existing_scaffold_single_input()` - Run with single input
- `test_experiment_scaffold_run()` - Run scaffold from experiments directory

### Mocking Strategy
- Mock `LLMFactory.create_llm()` to return `MockLLMInterface`
- Mock Docker build calls
- Use temporary directories for file operations
- Mock dataset loading when testing argument validation

## Example Workflows

### Generate from Examples and Evaluate
```bash
scaffold make run --data-dir data/crosswords --scaffolder-model gpt-4o --name solver --executor-model haiku --num-train-examples 5 --num-test-examples 10 --domain crosswords
```

### Create Baseline and Evaluate
```bash
scaffold make run --baseline --data-dir data/crosswords --name baseline-test --executor-model gpt-4o --num-train-examples 3 --num-test-examples 5 --domain crosswords --show-scoring-function
```

### Generate from Task Description
```bash
scaffold make --task "solve crosswords by analyzing clues" --scaffolder-model gpt-4o --name task-solver
```

### Run Task-Generated Scaffold
```bash
scaffold run --name task-solver --base-dir scaffolds/generated --executor-model haiku --input "1 Across: Small dog breed (3)"
```

### Evaluate Existing Scaffold
```bash
scaffold run --name my-scaffold --base-dir scaffolds/generated --executor-model haiku --data-dir data/crosswords --num-test-examples 20 --domain crosswords
```

### Run Experiment Scaffold
```bash
scaffold run --name 1-2-3 --base-dir experiments/crosswords_20250101_120000/scaffolds --executor-model gpt-4o --file puzzle.json --timeout 300
```

## Implementation Milestones

1. **Test Structure**: Write all unit tests for argument parsing and validation
2. **Parsing and Validation**: Implement argument parsing, validation, config dataclass
3. **Make Functionality**: Implement all three scaffold creation modes, directory structure
4. **Run Functionality**: Implement running with new logging, single vs multi-example
5. **Integration**: Main function, entry point, combined workflows
6. **Cleanup**: Remove old files, update documentation

## Validation Checklist
- [ ] All three generation modes work correctly
- [ ] Argument validation catches all invalid combinations
- [ ] Base directory inference works for make modes
- [ ] Run directories created only when needed
- [ ] Logs saved to correct locations for all scaffold sources
- [ ] Single and multi-example runs both work
- [ ] Test data loaded from test.jsonl (not valid.jsonl)
- [ ] Seeds properly applied to sampling
- [ ] Docker build integration preserved
- [ ] Timeout and thinking budget handled correctly
- [ ] Error messages are clear and actionable
- [ ] Existing scaffolds and experiments remain functional