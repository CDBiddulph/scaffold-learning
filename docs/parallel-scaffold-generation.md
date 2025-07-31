# Parallel Scaffold Generation Design

## Overview

This document outlines a simple parallelization strategy for initial scaffold generation in the scaffold learning framework. Unlike scaffold execution, this is purely about parallelizing LLM API calls without Docker or complex resource management.

## Current Sequential Implementation

In `experiment_runner.py`, the `_create_initial_scaffolds` method (lines 408-436) currently generates scaffolds sequentially:

```python
for scaffold_id, examples in self._get_training_examples(scaffold_ids).items():
    # Generate scaffold (LLM call)
    result = generate_scaffold(...)
    # Save scaffold (file I/O)
    self.file_manager.save_scaffold(scaffold_id=scaffold_id, result=result)
```

## Parallelization Opportunity

Each scaffold generation is completely independent:
- Different training examples per scaffold
- Independent LLM calls
- Separate file saves with unique IDs

This makes it trivial to parallelize with minimal complexity.

## Simple Implementation Strategy

### 1. Using concurrent.futures

```python
import concurrent.futures
from typing import Dict, List, Tuple

def _create_initial_scaffolds(self) -> List[str]:
    """Create initial scaffolds using random training examples in parallel."""
    scaffold_ids = [
        self._get_next_scaffold_id() for _ in range(self.initial_scaffolds)
    ]
    
    self.logger.info(f"Creating {self.initial_scaffolds} initial scaffolds")
    
    # Get all training examples upfront
    training_examples = self._get_training_examples(scaffold_ids)
    
    # Define generation function for parallel execution
    def generate_single_scaffold(scaffold_id: str, examples: List[DatasetExample]) -> Tuple[str, ScaffoldResult]:
        result = generate_scaffold(
            examples=examples,
            scaffolder_llm=self.scaffolder_llm,
            scoring_fn_code=self.scoring_fn_code,
            iteration=0,
            suggest_hack=self.suggest_hack,
        )
        return scaffold_id, result
    
    # Use ThreadPoolExecutor for I/O-bound LLM calls
    max_workers = min(self.initial_scaffolds, 5)  # Cap at 5 concurrent LLM calls
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_id = {
            executor.submit(generate_single_scaffold, sid, examples): sid
            for sid, examples in training_examples.items()
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_id):
            scaffold_id = future_to_id[future]
            try:
                _, result = future.result()
                # Save scaffold
                self.file_manager.save_scaffold(scaffold_id=scaffold_id, result=result)
                self.logger.info(f"Created initial scaffold {scaffold_id}")
            except Exception as e:
                self.logger.error(f"Failed to create scaffold {scaffold_id}: {e}")
                raise
    
    return scaffold_ids
```

### 2. With Progress Tracking

For better user experience, we can add progress tracking:

```python
def _create_initial_scaffolds(self) -> List[str]:
    """Create initial scaffolds with progress tracking."""
    scaffold_ids = [
        self._get_next_scaffold_id() for _ in range(self.initial_scaffolds)
    ]
    
    self.logger.info(f"Creating {self.initial_scaffolds} initial scaffolds in parallel")
    
    training_examples = self._get_training_examples(scaffold_ids)
    completed = 0
    
    def generate_and_track(scaffold_id: str, examples: List[DatasetExample]) -> Tuple[str, ScaffoldResult]:
        result = generate_scaffold(
            examples=examples,
            scaffolder_llm=self.scaffolder_llm,
            scoring_fn_code=self.scoring_fn_code,
            iteration=0,
            suggest_hack=self.suggest_hack,
        )
        return scaffold_id, result
    
    max_workers = min(self.initial_scaffolds, 5)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_and_track, sid, examples): sid
            for sid, examples in training_examples.items()
        }
        
        for future in concurrent.futures.as_completed(futures):
            scaffold_id = futures[future]
            try:
                _, result = future.result()
                self.file_manager.save_scaffold(scaffold_id=scaffold_id, result=result)
                completed += 1
                self.logger.info(
                    f"Created scaffold {scaffold_id} ({completed}/{self.initial_scaffolds})"
                )
            except Exception as e:
                self.logger.error(f"Failed to create scaffold {scaffold_id}: {e}")
                raise
    
    return scaffold_ids
```

### 3. With Rate Limiting Awareness

Since LLM interfaces already handle rate limiting internally (exponential backoff for Anthropic, retries for OpenAI), we mainly need to control concurrency:

```python
def _create_initial_scaffolds(self) -> List[str]:
    """Create initial scaffolds with adaptive concurrency."""
    scaffold_ids = [
        self._get_next_scaffold_id() for _ in range(self.initial_scaffolds)
    ]
    
    # Determine max workers based on LLM type
    model_spec = LLMFactory.resolve_model_spec(self.scaffolder_llm.get_model_info())
    if model_spec.startswith("anthropic/"):
        max_workers = 3  # More conservative for Anthropic
    elif model_spec.startswith("openai/"):
        max_workers = 5  # OpenAI tends to have higher rate limits
    else:
        max_workers = 10  # Mock/other providers
    
    # Cap based on number of scaffolds
    max_workers = min(self.initial_scaffolds, max_workers)
    
    self.logger.info(
        f"Creating {self.initial_scaffolds} initial scaffolds "
        f"(up to {max_workers} in parallel)"
    )
    
    # Rest of implementation as above...
```

## Parallel Scaffold Evolution

The same approach can be applied to scaffold evolution in `_evolve_scaffolds`:

```python
def _evolve_scaffolds(
    self,
    iteration: int,
    top_scaffold_runs: Dict[str, List[ScaffoldRunData]],
) -> List[str]:
    """Evolve selected scaffolds in parallel."""
    
    def evolve_single_scaffold(parent_id: str, run_data_list: List[ScaffoldRunData]) -> Tuple[str, ScaffoldResult]:
        evolved_result = evolve_scaffold(
            run_data=run_data_list,
            scaffolder_llm=self.scaffolder_llm,
            scoring_fn_code=self.scoring_fn_code,
            iteration=iteration,
            parent_scaffold_id=parent_id,
            suggest_hack=self.suggest_hack,
        )
        new_scaffold_id = self._get_next_scaffold_id(parent_id)
        return new_scaffold_id, evolved_result
    
    max_workers = min(len(top_scaffold_runs), 3)  # Conservative for evolution
    current_scaffold_ids = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(evolve_single_scaffold, parent_id, run_data): parent_id
            for parent_id, run_data in top_scaffold_runs.items()
        }
        
        for future in concurrent.futures.as_completed(futures):
            parent_id = futures[future]
            try:
                new_scaffold_id, result = future.result()
                self.file_manager.save_scaffold(
                    scaffold_id=new_scaffold_id,
                    result=result,
                )
                current_scaffold_ids.append(new_scaffold_id)
                self.logger.info(
                    f"Created evolved scaffold {new_scaffold_id} from {parent_id}"
                )
            except Exception as e:
                self.logger.error(f"Failed to evolve scaffold {parent_id}: {e}")
                raise
    
    return current_scaffold_ids
```

## Configuration Options

Add to `run_experiment.py`:

```python
parser.add_argument(
    "--parallel-scaffold-generation",
    action="store_true",
    default=True,
    help="Enable parallel scaffold generation (default: True)"
)
parser.add_argument(
    "--max-scaffold-workers",
    type=int,
    default=None,
    help="Maximum concurrent scaffold generation workers (default: auto-detect based on LLM)"
)
```

## Benefits

1. **Significant Speedup**: 3-5x faster initial scaffold generation
2. **Simple Implementation**: Uses standard library, no async complexity
3. **Built-in Rate Limiting**: LLM interfaces already handle retries
4. **No Resource Concerns**: Pure API calls, no Docker/memory issues
5. **Easy Rollback**: Simple flag to disable if needed

## Error Handling

The implementation preserves existing error behavior:
- If any scaffold generation fails, the entire experiment stops
- Errors are logged with context before re-raising
- LLM rate limit errors are handled by the LLM interfaces

## Testing Strategy

1. **Unit Test**: Verify parallel generation produces same scaffolds as sequential
2. **Integration Test**: Run small experiment with parallel generation
3. **Stress Test**: Generate many scaffolds to verify rate limiting works

## Implementation Priority

This is a high-value, low-risk optimization that should be implemented before the more complex parallel execution design. The speedup is immediate and significant, especially for experiments with many initial scaffolds.