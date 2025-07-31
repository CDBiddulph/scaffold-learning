# Parallel Execution Design for Scaffold Learning

## Overview

This document outlines the design for parallelizing scaffold execution in the scaffold learning framework, specifically targeting the `execute_scaffold` calls around line 457 in `experiment_runner.py`. The goal is to maximize parallelism while managing resource constraints and rate limits.

## Key Challenges

### 1. LLM Rate Limiting
- **Anthropic**: Sophisticated rate limiting with exponential backoff + retry-after headers
- **OpenAI**: Basic retry mechanism without sophisticated backoff
- **Impact**: Parallel execution will hit rate limits faster, requiring careful management

### 2. Docker Resource Constraints
- Each container consumes: 1GB RAM + 1 CPU core
- Running too many containers simultaneously could overwhelm system resources
- Timeout parameter adds complexity - slower systems might need adjustment

### 3. File I/O Race Conditions
- `get_new_execution_log_path` has a documented race condition (line 138 in `experiment_files.py`)
- Multiple threads could generate the same filename
- Need thread-safe file naming mechanism

### 4. Shared State Management
- `run_data_list` and `scores` require thread-safe updates
- Must maintain correct ordering of results

## Implementation Strategy

### 1. Controlled Parallelism with Semaphores

```python
import asyncio
import concurrent.futures
from threading import Lock
import threading

class ParallelExecutionManager:
    def __init__(self, max_concurrent_containers=4, max_concurrent_llm_calls=2):
        # Limit Docker containers to prevent resource exhaustion
        self.container_semaphore = threading.Semaphore(max_concurrent_containers)
        
        # Separate LLM rate limiting by provider
        self.anthropic_semaphore = threading.Semaphore(max_concurrent_llm_calls)
        self.openai_semaphore = threading.Semaphore(max_concurrent_llm_calls)
        
        # Thread-safe file naming
        self.file_counter_lock = Lock()
        self.file_counters = {}  # (iteration, scaffold_id, run_type) -> next_counter
        
        # Shared state protection
        self.shared_state_lock = Lock()
```

### 2. Thread-Safe File Naming

Replace the race-condition-prone `_get_next_run_id` with a thread-safe counter:

```python
def get_new_execution_log_path_threadsafe(
    self, iteration: int, scaffold_id: str, run_type: str
) -> Path:
    with self.file_counter_lock:
        key = (iteration, scaffold_id, run_type)
        if key not in self.file_counters:
            # Initialize based on existing files (one-time scan)
            self.file_counters[key] = self._count_existing_logs(iteration, scaffold_id, run_type)
        
        run_id = f"{run_type}_{self.file_counters[key]}"
        self.file_counters[key] += 1
        
        logs_dir = self._get_docker_logs_dir(iteration, scaffold_id)
        return logs_dir / f"{run_id}.log"
```

### 3. Async Scaffold Execution with Resource Management

```python
async def _execute_and_score_scaffold_async(
    self, iteration: int, scaffold_id: str, example: DatasetExample, 
    log_type: str, execution_manager: ParallelExecutionManager
) -> Tuple[ScaffoldExecutionResult, float]:
    
    # Get appropriate semaphore based on model
    model_spec = LLMFactory.resolve_model_spec(self.executor_model)
    if model_spec.startswith("anthropic/"):
        llm_semaphore = execution_manager.anthropic_semaphore
    elif model_spec.startswith("openai/"):
        llm_semaphore = execution_manager.openai_semaphore
    else:
        llm_semaphore = None  # mock/human models don't need rate limiting
    
    # Acquire both container and LLM semaphores
    with execution_manager.container_semaphore:
        if llm_semaphore:
            with llm_semaphore:
                return await self._do_execute_and_score(iteration, scaffold_id, example, log_type, execution_manager)
        else:
            return await self._do_execute_and_score(iteration, scaffold_id, example, log_type, execution_manager)

async def _do_execute_and_score(self, iteration, scaffold_id, example, log_type, execution_manager):
    # Thread-safe file path generation
    log_file_path = execution_manager.get_new_execution_log_path_threadsafe(
        iteration, scaffold_id, log_type
    )
    
    # Run in thread pool since execute_scaffold is blocking
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = loop.run_in_executor(executor, lambda: execute_scaffold(
            scaffold_dir=self.file_manager.get_scaffold_dir(scaffold_id),
            log_file_path=log_file_path,
            input_string=example.input,
            model_spec=self.executor_model,
            timeout=self.scaffold_timeout,
            console_output=False,
        ))
        result = await future
    
    # Calculate score
    if result.error_message is None:
        score = self.scoring_fn(result.output, example.scoring_data)
    else:
        logging.warning(f"Scaffold {scaffold_id} failed to execute: {result.error_message}")
        score = 0.0
        
    return result, score
```

### 4. Parallel Example Processing

```python
async def _run_scaffold_on_examples_parallel(
    self, iteration: int, scaffold_id: str, examples: List[DatasetExample],
    log_type: str, run_data_list: Optional[List[ScaffoldRunData]] = None,
    scaffold_code: Optional[str] = None,
) -> List[float]:
    
    execution_manager = ParallelExecutionManager(
        max_concurrent_containers=min(4, len(examples)),  # Don't over-parallelize small sets
        max_concurrent_llm_calls=2  # Conservative rate limiting
    )
    
    # Create tasks for all examples
    tasks = [
        self._execute_and_score_scaffold_async(
            iteration, scaffold_id, example, log_type, execution_manager
        )
        for example in examples
    ]
    
    # Execute all in parallel with progress tracking
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and update shared state thread-safely
    scores = []
    with execution_manager.shared_state_lock:
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Example {i} failed: {result}")
                scores.append(0.0)
                continue
                
            execution_result, score = result
            scores.append(score)
            
            # Update run_data_list if provided
            if run_data_list is not None:
                if scaffold_code is None:
                    raise ValueError("Scaffold code is required for ScaffoldRunData")
                run_data_list.append(ScaffoldRunData(
                    code=scaffold_code,
                    execution_log=execution_result.stderr,
                    example=examples[i],
                    actual_output=execution_result.output,
                    score=score,
                ))
    
    # Log results
    log_type_str = "validation" if log_type == "valid" else "training"
    scores_str = ", ".join(f"{s:.3f}" for s in scores)
    if len(scores) > 1:
        maybe_s, average_str = "s", f" (avg {np.mean(scores):.3f})"
    else:
        maybe_s, average_str = "", ""
    self.logger.info(
        f"Scaffold {scaffold_id} {log_type_str} score{maybe_s}: {scores_str}{average_str}"
    )
    
    return scores
```

### 5. Integration Points

1. Replace `_run_scaffold_on_examples` calls with `_run_scaffold_on_examples_parallel`
2. Add `asyncio.run()` wrapper in calling methods:
   - `_validate_scaffolds`
   - `_run_training`
3. Make parent methods async where needed

Example integration:
```python
def _validate_scaffolds(self, iteration: int, scaffold_ids: List[str], 
                       validation_sample: List[DatasetExample]) -> Dict[str, List[float]]:
    """Validate a list of scaffolds and return their scores."""
    validation_scores = {}
    
    # Run async validation
    async def run_validations():
        tasks = []
        for scaffold_id in scaffold_ids:
            task = self._run_scaffold_on_examples_parallel(
                iteration, scaffold_id, validation_sample, "valid"
            )
            tasks.append((scaffold_id, task))
        
        results = await asyncio.gather(*[task for _, task in tasks])
        return dict(zip([sid for sid, _ in tasks], results))
    
    validation_scores = asyncio.run(run_validations())
    return validation_scores
```

## Configuration Recommendations

### Resource Limits
- **Max Concurrent Containers**: 4 (conservative default for 8GB+ systems)
- **Max Concurrent LLM Calls**: 2 per provider (avoid rate limits)
- **Adaptive Sizing**: Scale down for small example sets to avoid overhead

### Environment Variables
Consider adding these configuration options:
```bash
SCAFFOLD_MAX_CONCURRENT_CONTAINERS=4
SCAFFOLD_MAX_CONCURRENT_LLM_CALLS=2
SCAFFOLD_PARALLEL_EXECUTION=true
```

### Command-Line Arguments
Add to `run_experiment.py`:
```python
parser.add_argument(
    "--max-concurrent-containers",
    type=int,
    default=4,
    help="Maximum number of Docker containers to run in parallel"
)
parser.add_argument(
    "--max-concurrent-llm-calls",
    type=int,
    default=2,
    help="Maximum number of concurrent LLM API calls per provider"
)
parser.add_argument(
    "--disable-parallel",
    action="store_true",
    help="Disable parallel execution (run sequentially)"
)
```

## Expected Performance Gains

Based on the analysis of execution patterns:

1. **Scaffold Validation**: Up to 4x speedup (biggest bottleneck)
   - Multiple scaffolds validated in parallel
   - Each scaffold runs on multiple examples in parallel

2. **Training Runs**: 2-3x speedup for multi-example training
   - Parallel example execution within each scaffold

3. **Overall Experiment Time**: 30-50% reduction
   - Depends on experiment configuration
   - Larger experiments see more benefit

## Risk Mitigation

### Fallback Strategy
Include a `--disable-parallel` flag to revert to sequential execution if issues arise.

### Resource Monitoring
Log resource usage to detect when limits are being hit:
```python
def log_resource_usage():
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    docker_count = len([p for p in psutil.process_iter() if 'docker' in p.name()])
    
    logging.info(f"Resources: CPU={cpu_percent}%, Memory={memory.percent}%, Docker={docker_count}")
```

### Graceful Degradation
If resources are constrained, automatically reduce parallelism:
```python
def adaptive_parallelism(base_limit: int) -> int:
    memory = psutil.virtual_memory()
    if memory.percent > 80:
        return max(1, base_limit // 2)
    return base_limit
```

## Implementation Priority

1. **Phase 1**: Implement parallel validation (highest impact)
2. **Phase 2**: Add parallel training execution
3. **Phase 3**: Parallelize initial scaffold generation
4. **Phase 4**: Add adaptive resource management

## Testing Strategy

1. **Unit Tests**: Test thread-safe file naming
2. **Integration Tests**: Verify correct parallel execution
3. **Load Tests**: Ensure system stability under high parallelism
4. **Regression Tests**: Verify identical results with sequential execution