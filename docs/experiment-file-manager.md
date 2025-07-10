# Experiment File Manager Refactoring

This document describes the refactoring of the ExperimentFileManager to use a flat scaffold directory structure and encapsulate all file system access.

## Overview

The refactoring eliminates the `new/` and `old/` directory structure for scaffolds, instead saving all scaffolds directly into `experiments/<exp_id>/scaffolds/`. This simplifies the file structure, removes unnecessary copying operations, and ensures that ExperimentFileManager is the sole owner of all file paths.

## New Directory Structure

```
experiments/
└── experiment_name_{timestamp}/
    ├── metadata.json
    ├── scaffolds/
    │   ├── 0/
    │   │   ├── scaffold.py
    │   │   ├── metadata.json
    │   │   ├── llm_executor.py
    │   │   └── llm_interfaces.py
    │   ├── 1/
    │   ├── 2/
    │   ├── 0-0/
    │   ├── 1-0/
    │   └── 2-0/
    ├── logs/
    │   ├── 0/
    │   │   ├── 0/
    │   │   │   ├── train_0.log
    │   │   │   ├── train_1.log
    │   │   │   ├── valid_0.log
    │   │   │   └── valid_1.log
    │   │   └── 1/
    │   └── 1/
    │       ├── 0/
    │       ├── 1/
    │       └── 0-0/
    └── scoring/
        ├── scores_0.json
        ├── scores_1.json
        └── scores_2.json
```

## Key Changes

1. **Scaffolds**: Saved directly to `scaffolds/<scaffold_id>/` regardless of iteration
2. **Logs**: Organized by iteration then scaffold ID: `logs/<iteration>/<scaffold_id>/`
3. **Scores**: Saved to `scoring/scores_<iteration>.json`
4. **No Copying**: Scaffolds execute from their original save location

## Interface Changes

### ExperimentFileManager

#### Deleted Public Methods

- `copy_scaffold(from_path: Path, to_iteration: int, to_scaffold_id: str) -> Path`
- `find_scaffold_iteration(scaffold_id: str) -> int`
- `list_scaffolds(iteration: int) -> List[str]`
- `get_scaffold_path(iteration: int, scaffold_id: str) -> Path`
- `get_logs_path(iteration: int, scaffold_id: str, run_type: str) -> Path`

#### Modified Public Methods

```python
def save_scaffold(self, scaffold_id: str, result: ScaffoldResult) -> None:
    """Save a scaffold to the experiment directory.
    
    Args:
        scaffold_id: Unique identifier for this scaffold
        result: ScaffoldResult containing code and metadata
    
    Raises:
        OSError: If scaffold cannot be saved
    """
```

```python
def load_scaffold(self, scaffold_id: str) -> ScaffoldResult:
    """Load a scaffold from disk.
    
    Args:
        scaffold_id: Scaffold identifier
    
    Returns:
        ScaffoldResult with code and metadata
    
    Raises:
        FileNotFoundError: If scaffold doesn't exist
    """
```

```python
def save_scores(self, iteration: int, train_scores: Dict[str, float], valid_scores: Dict[str, float]) -> None:
    """Save training and validation scores for an iteration.
    
    Args:
        iteration: Iteration number
        train_scores: Dictionary mapping scaffold_id to training score
        valid_scores: Dictionary mapping scaffold_id to validation score
    """
```

```python
def load_scores(self, iteration: int) -> Dict[str, Dict[str, float]]:
    """Load scores from a previous iteration.
    
    Args:
        iteration: Iteration number to load
    
    Returns:
        Dictionary mapping "train" and "valid" to their respective scores
    
    Raises:
        FileNotFoundError: If scoring file doesn't exist for iteration
    """
```

#### New Public Methods

```python
def get_docker_scaffold_dir(self, scaffold_id: str) -> Path:
    """Get scaffold directory path for Docker mounting.
    
    Args:
        scaffold_id: Scaffold identifier
    
    Returns:
        Absolute path to scaffold directory
    
    Raises:
        FileNotFoundError: If scaffold doesn't exist
    """
```

```python
def get_docker_logs_dir(self, iteration: int, scaffold_id: str) -> Path:
    """Get logs directory path for Docker mounting.
    
    Args:
        iteration: Iteration number
        scaffold_id: Scaffold identifier
    
    Returns:
        Absolute path to logs directory
    """
```

### execute_scaffold Function

The signature changes to accept a file manager instead of paths:

```python
def execute_scaffold(
    file_manager: 'ExperimentFileManager',
    scaffold_id: str,
    iteration: int,
    run_type: str,
    input_string: str,
    model: str,
    timeout: int = 120,
) -> ScaffoldExecutionResult:
    """Execute a scaffold in a Docker container with the given input.
    
    Args:
        file_manager: ExperimentFileManager instance for path resolution
        scaffold_id: Scaffold identifier to execute
        iteration: Iteration number for logging
        run_type: Type of run (e.g., 'train_0', 'valid_1')
        input_string: Input to pass to the scaffold's process_input function
        model: Model name for the executor LLM
        timeout: Maximum execution time in seconds
    
    Returns:
        ScaffoldExecutionResult with output, stderr, exit code, and execution time
    """
```

## Implementation Strategy

### Phase 1: Test Updates

1. Write new tests for `get_docker_scaffold_dir()` and `get_docker_logs_dir()`
2. Update all existing tests to expect the new directory structure
3. Remove tests for deleted methods
4. Run `pytest` to ensure tests fail as expected

### Phase 2: ExperimentFileManager Refactoring

1. Remove all deleted methods
2. Update save/load methods to use flat scaffold structure
3. Implement new Docker path methods
4. Update score save/load to use new location
5. Run tests to verify file manager works correctly

### Phase 3: Interface Updates

1. Update `execute_scaffold()` to accept file manager and IDs
2. Update all calls in ExperimentRunner
3. Remove all direct path manipulation
4. Fix scaffold ID collection from scores instead of directory listing

### Phase 4: Final Validation

1. Run complete test suite
2. Verify no file paths leak from ExperimentFileManager
3. Test end-to-end experiment execution

## Benefits

1. **Simpler Structure**: No more confusing `new/` and `old/` directories
2. **No Copying**: Scaffolds run from their original location
3. **Better Encapsulation**: File paths never leave ExperimentFileManager (except for Docker)
4. **Cleaner Interface**: Methods work with IDs and iteration numbers, not paths
5. **Easier Testing**: Simpler directory structure to verify

## Migration Notes

- No backward compatibility is maintained
- Existing experiments will not work with the new system
- This is acceptable as there is only one user of the system