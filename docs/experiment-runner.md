# Experiment Runner Implementation

This document describes the implementation of the experiment runner feature for scaffold learning.

## Overview

The experiment runner automatically generates and evolves scaffolds through iterative learning. It:
1. Creates initial scaffolds from training examples
2. Evaluates scaffolds on validation data
3. Selects top-performing scaffolds and evolves them based on training runs
4. Repeats for multiple iterations to find the best scaffold

## Key Design Decisions

### Directory Structure

```
experiments/
└── experiment_name_{timestamp}/
    ├── metadata.json
    └── iterations/
        ├── 0/
        │   ├── scaffolds/
        │   │   └── new/
        │   │       ├── 0/
        │   │       │   ├── metadata.json
        │   │       │   └── scaffold.py
        │   │       ├── 1/
        │   │       └── 2/
        │   └── scoring.json
        └── 1/
            ├── scaffolds/
            │   ├── old/
            │   │   ├── 0/
            │   │   ├── 1/
            │   │   └── 2/
            │   └── new/
            │       ├── 0-0/
            │       ├── 1-0/
            │       └── 2-0/
            ├── logs/
            │   ├── 0/
            │   │   ├── train.json
            │   │   ├── train.log
            │   │   ├── valid.json
            │   │   └── valid.log
            │   └── ...
            └── scoring.json
```

- Iterations have `scaffolds/old/` (copied from previous) and `scaffolds/new/` (evolved versions)
- Logs are saved under `logs/scaffold_id/run_type.{json,log}`

### Scaffold ID System

- Initial scaffolds: `0`, `1`, `2`, ...
- Derived scaffolds: `parent-0`, `parent-1`, ...
- Example: `2-0` is the first evolution of scaffold `2`
- Example: `2-0-0` is the first evolution of scaffold `2-0`

### Data Structures

All shared data structures are in `src/scaffold_learning/core/data_structures.py`:

- `DatasetExample`: Represents a training/validation example with id, input, and scoring_data
- `ScaffoldMetadata`: Tracks creation time, model, parent scaffold, iteration
- `ScaffoldResult`: Contains scaffold code and metadata
- `ScaffoldExecutionResult`: Output, stderr, exit code, execution time
- `ScaffoldRunData`: All data from a run needed for evolution

### Error Handling

- Failed scaffold execution: Score of 0.0, continue experiment
- Failed scaffold generation: Retry 3 times, then skip with warning
- If a scaffold can't be evolved, find the next best scaffold to evolve
- Structure code to yield additional top scaffolds if initial ones fail

### Smart Validation Strategy

- Randomize validation examples at the start of each iteration
- Use the same validation subset throughout that iteration for consistency
- Iteration 0: Generate initial scaffolds but don't validate them
- Later iterations: Validate new scaffolds first, then selectively validate historical scaffolds only as needed to determine the top K
- Use most recent validation scores for ranking scaffolds before validation begins
- This ensures efficient validation while maintaining fair comparison

### Scaffold ID Generation Logic

- Initial scaffolds get numeric IDs: "0", "1", "2", etc.
- Evolved scaffolds append "-N" to parent ID
- First evolution of "2" becomes "2-0"
- First evolution of "2-0" becomes "2-0-0"
- Track next available number for each parent scaffold

### Progress Reporting

- Use logging.info() for real-time progress updates
- Show format: `[Iteration 2] Evaluating scaffold 2-0: validation score 0.75`
- Log when starting/finishing major operations
- Show current best scaffold after each iteration

### Random Seed Handling

- Set random.seed() at experiment start
- Save seed in experiment metadata.json
- Use for reproducible training example selection
- Log the seed being used

## Implementation Details

### Files to Create/Modify

#### 1. CREATE: `src/scaffold_learning/core/data_structures.py` (~100 lines)

**Dataclasses to create:**
- `DatasetExample`: id (str), input (str), scoring_data (Dict[str, Any])
- `ScaffoldMetadata`: created_at (str), model (Optional[str]), parent_scaffold_id (Optional[str]), iteration (int)
- `ScaffoldResult`: code (str), metadata (ScaffoldMetadata)
- `ScaffoldExecutionResult`: output (str), stderr (str), exit_code (int), execution_time (float)
- `ScaffoldRunData`: code (str), execution_log (str), example (DatasetExample), actual_output (str), score (float)

#### 2. CREATE: `src/scaffold_learning/core/scaffold_generation.py` (~150 lines)

**Public methods:**
- `generate_scaffold(prompt: str, scaffolder_llm: LLMInterface, examples: List[DatasetExample]) -> ScaffoldResult`
  - Called by: ExperimentRunner._create_initial_scaffolds()
  - Constructs prompt with task description and examples
  - Parses LLM response to extract Python code
  - Creates metadata with timestamp and iteration

- `evolve_scaffold(run_data: ScaffoldRunData, scaffolder_llm: LLMInterface) -> ScaffoldResult`
  - Called by: ExperimentRunner._run_evolution_iteration()
  - Shows previous code, logs, score to LLM
  - Asks for evolution to maximize score
  - Parses response and creates new metadata

**Refactoring needed:**
- Extract prompt construction from generate_scaffold_script.py
- Extract code parsing logic (finding ```python blocks)
- Make functions return values instead of writing files

#### 3. CREATE: `src/scaffold_learning/core/scaffold_execution.py` (~200 lines)

**Public methods:**
- `execute_scaffold(scaffold_dir: Path, input_string: str, model: str, logs_path: Path, timeout: int = 120) -> ScaffoldExecutionResult`
  - Called by: ExperimentRunner._evaluate_scaffold() and _run_training_example()
  - Builds Docker command with proper mounts
  - Captures output, stderr, execution time
  - Handles timeouts gracefully
  - Saves logs to specified path

**Refactoring needed:**
- Extract Docker command building from run_scaffold.py
- Make timeout a parameter
- Return structured result instead of printing

#### 4. CREATE: `src/scaffold_learning/core/experiment_files.py` (~250 lines)

**Class: ExperimentFileManager**

Public methods:
- `__init__(self, experiment_dir: Path)` - Called by: ExperimentRunner.__init__
- `save_scaffold(self, iteration: int, scaffold_id: str, result: ScaffoldResult) -> Path` - Called by: ExperimentRunner
- `load_scaffold(self, iteration: int, scaffold_id: str) -> ScaffoldResult` - Called by: ExperimentRunner
- `get_scaffold_path(self, iteration: int, scaffold_id: str) -> Path` - Called by: ExperimentRunner
- `save_scores(self, iteration: int, train_scores: Dict[str, float], valid_scores: Dict[str, float])` - Called by: ExperimentRunner
- `load_scores(self, iteration: int) -> Tuple[Dict[str, float], Dict[str, float]]` - Called by: ExperimentRunner
- `save_experiment_metadata(self, metadata: Dict[str, Any])` - Called by: ExperimentRunner.__init__
- `get_logs_path(self, iteration: int, scaffold_id: str, run_type: str) -> Path` - Called by: ExperimentRunner
- `copy_scaffold(self, from_path: Path, to_iteration: int, to_scaffold_id: str) -> Path` - Called by: ExperimentRunner

Must also copy llm_executor.py and llm_interfaces.py when saving scaffolds.

#### 5. CREATE: `src/scaffold_learning/core/experiment_runner.py` (~400 lines)

**Class: ExperimentRunner**

Public methods:
- `__init__(...)` - Called by: run_experiment.main()
- `run(self) -> Path` - Called by: run_experiment.main()

Key private methods that orchestrate the flow:
- `_create_initial_scaffolds()`: Generate initial scaffolds with random examples
- `_run_evolution_iteration()`: Main iteration logic for evolution cycles
- `_evaluate_scaffold()`: Run on validation set
- `_select_top_scaffolds()`: Pick best K scaffolds
- `_run_training_example()`: Execute on training data
- `_evolve_scaffolds()`: Generate evolved versions
- `_get_next_scaffold_id()`: Generate IDs like 0, 1, 2, then 0-0, 1-0

#### 6. CREATE: `src/scaffold_learning/cli/run_experiment.py` (~200 lines)

**Public method:**
- `main() -> None` - Entry point
  - Parse arguments with argparse
  - Load JSONL data into DatasetExample objects
  - Create scoring function lambda wrapping crosswords.score
  - Create ExperimentRunner and call run()
  - Print best scaffold path and score

#### 7. MODIFY: `src/scaffold_learning/cli/generate_scaffold_script.py` (250 → 100 lines)
- Extract prompt generation and code parsing to scaffold_generation.py
- Update main() to call new functions
- Handle optional model argument (can be None now)

#### 8. MODIFY: `src/scaffold_learning/cli/run_scaffold.py` (300 → 150 lines)
- Extract Docker execution to scaffold_execution.py
- Update main() to call execute_scaffold()
- Read model from metadata.json if not provided

### File Management

The `ExperimentFileManager` class handles all file I/O:
- Never construct paths manually - always use the file manager
- Provides methods for scaffold saving/loading, score persistence, log paths
- Ensures consistent directory structure

### Scaffold Generation

- `generate_scaffold()`: Shows task description and multiple examples to LLM
- `evolve_scaffold()`: Shows previous code, execution logs, score, and asks for evolution
- Both return `ScaffoldResult` with code and metadata

### Scaffold Execution

- Runs in Docker container for isolation
- Accepts custom logs path for organized output
- Returns structured `ScaffoldExecutionResult`
- Model must be specified (read from metadata if needed)

### Experiment Runner

The `ExperimentRunner` orchestrates the entire process:

1. Create initial scaffolds showing random training examples (iteration 0, no validation)
2. For each subsequent iteration:
   - Select validation subset for this iteration
   - Validate newly created scaffolds first
   - Select top K scaffolds:
     - Order scaffolds by most recent validation scores (new scaffolds first)
     - Validate scaffolds as needed until top K are all validated this iteration
   - Copy selected scaffolds to old/ directory
   - Run each on a training example
   - Generate evolved versions based on training performance
   - Save evolved scaffolds to new/ directory

### CLI Interface

`run_experiment.py` provides the command-line interface:
- Load train/valid data from JSONL files
- Create scoring function (hardcoded to crosswords for now)
- Configure experiment parameters
- Run experiment and report best scaffold

## Future Extensions

### Multi-file Scaffolds
- File manager already supports arbitrary directory structures
- Scaffold generation will need to parse multiple code blocks
- Execution will remain the same (Docker mounts the directory)

### Agent-based Scaffolding
- Scaffolder will interact over multiple steps
- Will need to maintain conversation state
- Can reuse existing LLM interfaces

### Resource Management
- Execution timeout will become dynamic based on scaffold complexity
- Track API credits and time usage
- Provide resource checking functions to executor

### Experiment Resumption
- File structure already supports reading partial experiments
- Would need to detect incomplete iterations
- Resume from last completed scaffold

## What Existing Code to Reuse

### From `generate_scaffold_script.py`:
- **Where**: scaffold_generation.py
- **What**: Prompt construction, LLM response parsing for ```python blocks
- **How**: Extract functions, make them accept examples list, return values instead of writing files

### From `run_scaffold.py`:
- **Where**: scaffold_execution.py  
- **What**: Docker command building, container execution, output streaming
- **How**: Extract Docker logic, make timeout parameter, return structured result

### From `llm_interfaces.py`:
- **Where**: Throughout for LLM interactions
- **What**: LLMFactory.from_string(), all interface classes
- **How**: Use as-is

### From `domains/crosswords/score.py`:
- **Where**: run_experiment.py
- **What**: score() function
- **How**: Wrap in lambda to match signature (expected, scoring_data)

### From `utils.py`:
- **Where**: Multiple files
- **What**: setup_logging(), get_api_key()
- **How**: Use as-is

### Support files:
- **What**: llm_executor.py, llm_interfaces.py
- **How**: Copy into scaffold directories when saving

## Testing Strategy

### Tests to Create

1. **`tests/core/test_data_structures.py`**:
   - Test dataclass initialization
   - Test JSON serialization of ScaffoldMetadata
   - Test field access and types

2. **`tests/core/test_scaffold_generation.py`**:
   - Test prompt construction with multiple examples
   - Test code extraction from LLM responses
   - Test metadata creation with timestamps
   - Test handling of malformed responses (no code blocks)
   - Test retry logic for failed generation

3. **`tests/core/test_scaffold_execution.py`**:
   - Test Docker command construction
   - Test timeout handling (mock subprocess)
   - Test result dataclass population
   - Test logs saved to correct path
   - Test error handling for failed execution

4. **`tests/core/test_experiment_files.py`**:
   - Test directory structure creation
   - Test scaffold saving with all required files
   - Test scaffold loading and metadata parsing
   - Test score persistence and loading
   - Test path generation for different scaffold IDs
   - Test copy_scaffold preserves all files

5. **`tests/core/test_experiment_runner.py`**:
   - Test initial scaffold creation with mock LLM
   - Test scaffold ID generation (0, 1, 2, then 0-0, 1-0)
   - Test top-K selection with rescoring
   - Test handling of failed scaffolds (score 0)
   - Test validation subset consistency within iteration
   - Test finding additional scaffolds when improvement fails

6. **`tests/cli/test_run_experiment.py`**:
   - Integration test with mock LLMs and small dataset
   - Test CLI argument parsing
   - Test JSONL data loading into DatasetExample objects
   - Test final output shows path and score

## Implementation Milestones

### Milestone 1: Create shared data structures
- Write tests for dataclass creation and JSON serialization
- Implement all dataclasses in `data_structures.py`
- Verify ScaffoldMetadata can round-trip to/from JSON

### Milestone 2: Refactor scaffold generation
- Write tests for prompt construction with examples
- Write tests for code extraction from LLM responses
- Extract and refactor code from `generate_scaffold_script.py`
- Update `generate_scaffold_script.py` to use new functions

### Milestone 3: Refactor scaffold execution  
- Write tests for Docker execution with custom logs path
- Write tests for result dataclass creation
- Extract Docker logic from `run_scaffold.py`
- Update `run_scaffold.py` to use new execution function

### Milestone 4: Implement experiment file management
- Write tests for all file operations
- Write tests for path generation
- Implement `ExperimentFileManager` class
- Test directory structure matches specification

### Milestone 5: Implement experiment runner
- Write tests for scaffold ID generation
- Write tests for scoring and selection logic
- Implement `ExperimentRunner` class with all iteration logic
- Test complete experiment flow with mocks

### Milestone 6: Create CLI and integration
- Write integration tests with mock components
- Implement argument parsing in `run_experiment.py`
- Add data loading from JSONL files
- Test end-to-end with real crossword data

## Additional Implementation Details

### Method Stubs and Signatures

The documentation above includes the key public methods. Here are additional details:

**Key functions**:
- `generate_scaffold()`: Creates new scaffolds by showing task description and training examples to the scaffolder LLM
- `evolve_scaffold()`: Creates evolved versions by showing previous code, execution logs, and scores to the scaffolder LLM

### Prompt Construction Details

For generate_scaffold:
- Show the task prompt
- For each example, show "Input:" and "Expected output:"
- Ask LLM to write a scaffold.py that processes inputs

For evolve_scaffold:
- Show the previous scaffold code
- Show the execution logs
- Show input, actual output, expected output
- Show the score
- Ask LLM to evolve the scaffold to maximize the score

### JSONL Data Loading

When loading train/valid data:
- Each line has fields: id, input, and potentially others
- Create DatasetExample with scoring_data containing all fields except id and input
- For crosswords, scoring_data will contain {"solution": "..."}

### Scoring Function Wrapper

The crosswords score function needs to be wrapped to match the expected signature of `(expected, scoring_data) -> float`.

### Smart Validation Strategy

The algorithm efficiently selects the top K scaffolds by validating only as needed:

1. **Initial ordering**: New scaffolds (never validated) first, then historical scaffolds by most recent validation score
2. **Validation loop**: 
   - Check if top K scaffolds are all validated this iteration
   - If not, validate the highest-ranked scaffold that hasn't been validated this iteration
   - Resort the list with the new score
   - Repeat until top K are all validated this iteration
3. **Early termination**: If new scaffolds are excellent, historical scaffolds may never need validation

### Retry Logic for Generation

Failed scaffold generation is retried up to 3 times before skipping the scaffold with a warning.

## Configuration

Key parameters:
- `--experiment-name`: Name for this experiment run
- `--num-iterations`: How many improvement cycles
- `--scaffolds-per-iter`: How many top scaffolds to improve
- `--initial-scaffolds`: How many to create initially
- `--num-validation-examples`: Size of validation subset
- `--scaffolder-model`: Which LLM to use for generation

## Example Usage

```bash
python -m src.scaffold_learning.cli.run_experiment \
    --experiment-name crossword-test \
    --num-iterations 3 \
    --scaffolds-per-iter 5 \
    --initial-scaffolds 10 \
    --num-validation-examples 20 \
    --scaffolder-model gpt-4o
```

This will:
1. Create 10 initial scaffolds
2. Run 3 iterations
3. Evolve top 5 scaffolds each iteration
4. Use 20 validation examples for scoring
5. Use GPT-4o for scaffold generation

## Things to Remember During Implementation

1. All paths must go through ExperimentFileManager - never construct paths manually
2. Model can be None in scaffold metadata (when not specified during generation)
3. When copying scaffolds, must copy all files including llm_executor.py and llm_interfaces.py
4. Validation examples are randomized per iteration but consistent within iteration
5. Always log progress at INFO level for user visibility
6. Handle failures gracefully - failed scaffolds get score 0 but experiment continues
7. Track which scaffold IDs have been used to avoid duplicates
8. The first iteration (0) uses scaffolds/new/ (not scaffolds/) to maintain consistency
9. When generating scaffold IDs, maintain a counter for each parent (e.g., {"2": 0, "2-0": 0})
10. ExperimentRunner should check scaffolds_per_iter <= initial_scaffolds in __init__

## External Libraries

No external libraries needed - using only Python standard library:
- argparse for CLI
- json for data loading
- pathlib for file paths
- datetime for timestamps
- random for sampling
- logging for progress
- subprocess (already used in run_scaffold.py)
- shutil for copying files

## Data Paths

Default paths for crossword domain:
- Training data: `src/scaffold_learning/domains/crosswords/data/train.jsonl`
- Validation data: `src/scaffold_learning/domains/crosswords/data/valid.jsonl`

These should be configurable via CLI arguments in the future.

## Smart Validation Algorithm Details

The scaffold selection algorithm efficiently determines the top K scaffolds by validating only as needed:

1. **Initial ordering**: Create a list with new scaffolds first (they have no historical scores), followed by historical scaffolds ordered by their most recent validation scores
2. **Validation loop**: Check if the top K scaffolds have all been validated this iteration. If not, validate the highest-ranked scaffold that hasn't been validated this iteration, then resort the list with the new score
3. **Termination**: Continue until the top K scaffolds are all validated this iteration

## Complete List of Files in Each Scaffold Directory

When saving a scaffold, these files must be present:
1. `scaffold.py` - The main scaffold code
2. `metadata.json` - Creation time, model, parent_scaffold_id, iteration
3. `llm_executor.py` - Copy from scaffold-scripts/
4. `llm_interfaces.py` - Copy from src/scaffold_learning/core/

## Notes from User Requirements

From the original specification:
- Show only one training example to scaffolder (for now)
- In the future, will show multiple examples
- Scaffolder should never see validation data or scores
- Final output should print both path and score of best scaffold
- Experiment name should be a CLI argument
- scoring.json contains both train and valid scores in one file

## Important Clarifications from Discussion

1. **Scaffold directory structure**: 
   - Originally mentioned just scaffolds/, but clarified to use scaffolds/old/ and scaffolds/new/
   - Even iteration 0 should use scaffolds/new/ for consistency

2. **Model argument in generate_scaffold**:
   - Not needed - scaffolder doesn't need to know executor model
   - Existing generate_scaffold_script.py will need to handle optional model

3. **Scaffold copying**:
   - Needed to carry forward top scaffolds between iterations
   - Copy from previous iteration's new/ to current iteration's old/

4. **Failed generation handling**:
   - Retry 3 times before giving up
   - If scaffold can't be evolved, continue with next best scaffold
   - Structure code to easily yield additional top scaffolds

5. **Validation sampling**:
   - Randomize at start of each iteration
   - Keep same subset throughout iteration for consistency

6. **Scoring function signature**:
   - Takes (expected, scoring_data) not (expected, actual)
   - Wrap crosswords.score() appropriately

7. **DatasetExample structure**:
   - scoring_data contains all fields except id and input
   - For crosswords: scoring_data = {"solution": "..."}

8. **Files to copy when saving scaffold**:
   - llm_executor.py from scaffold-scripts/
   - llm_interfaces.py from src/scaffold_learning/core/

9. **Task prompt for experiment**:
   - User will provide this as part of the experiment setup
   - Not hardcoded - should be configurable

10. **Default executor model**:
    - run_scaffold.py needs to read from metadata if not provided
    - run_experiment.py must always specify model when executing

## CLI Arguments to Add

For run_experiment.py:
- `--experiment-name` (required): Name for the experiment
- `--num-iterations` (default: 5): Number of evolution iterations
- `--scaffolds-per-iter` (default: 3): Top scaffolds to evolve each iteration
- `--initial-scaffolds` (default: 5): Number of initial scaffolds to create
- `--num-validation-examples` (default: 10): Validation examples per iteration
- `--scaffolder-model` (required): LLM model for scaffold generation
- `--executor-model` (default: "gpt-4-turbo"): LLM model for scaffold execution
- `--task-prompt` (required): Description of what the scaffold should do

Note: In the future, will add:
- `--train-data`: Path to training JSONL
- `--valid-data`: Path to validation JSONL
- `--domain`: Which domain to use (currently hardcoded to crosswords)