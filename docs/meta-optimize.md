# Meta-Optimize Domain Implementation Plan

## Overview

The meta-optimize domain is a meta-level domain where scaffolds optimize the average score across multiple mesa-domain examples. Unlike regular domains where scaffolds solve individual problems, meta-optimize scaffolds receive a batch of mesa-domain examples and must develop strategies to maximize the average score across all of them.

The scaffold can iteratively call the mesa-domain's scoring function to test different approaches and discover optimal strategies.

### Example Use Case
A meta-optimize scaffold might receive 3 reward-model prompts and need to generate responses that maximize the average reward score. The scaffold can test different response strategies by calling the scoring function before submitting final answers.

## Final Design Decisions

### Confirmed Architecture Choices
- **Domain name**: meta-optimize
- **Parameter format**: JSON for mesa-params (e.g., `--domain-param mesa-params='{"rm":"llm:haiku"}'`)
- **Docker networking**: Use `host.docker.internal` for Docker-to-host communication
- **Server port**: Fixed at 8080 (hardcoded)
- **Server lifecycle**: Start in create_scoring_function(), cleanup via atexit
- **HTTP library**: Flask for server, requests for client
- **Module name**: `scaffold_tools` (imported as `from scaffold_tools import score`)
- **File organization**: Server in `src/scaffold_learning/core/`, client in `src/scaffold_learning/runtime/`
- **Error handling**: Let failures propagate naturally (no special handling)
- **Timeout**: User-configured (not auto-scaled)
- **Testing**: TDD with unit tests for each milestone
- **Sampling**: Use ExampleSampler without replacement, seed default 42
- **Health check**: Simple check if server is running before scaffold execution
- **Prompt location**: Domain-specific instructions as part of task description

## Architecture

### Key Concepts

1. **Mesa-domain**: The underlying domain being optimized (e.g., reward-model, crosswords)
2. **Meta-domain**: The meta-optimize domain that operates on batches of mesa-examples
3. **Meta-example**: Contains a list of mesa-domain scoring_data entries
4. **Mesa-scorer API**: External scoring service accessible to scaffolds

### Data Flow

```
Meta-example (input):
{
  "scoring_data": [
    {"input": "3+1", ...mesa-specific fields...},
    {"input": "1+2", ...mesa-specific fields...},
    {"input": "2+3", ...mesa-specific fields...}
  ]
}

Scaffold output:
["answer1", "answer2", "answer3"]

Meta-score:
mean([mesa_score(answer1, data1), mesa_score(answer2, data2), mesa_score(answer3, data3)])
```

## Implementation Details

### 1. Directory Structure

```
src/scaffold_learning/domains/meta_optimize/
├── __init__.py
├── prepare_datasets.py
├── score.py
└── data/
    ├── train.jsonl
    └── valid.jsonl

src/scaffold_learning/core/
└── scaffold_tools_server.py  # Server component

src/scaffold_learning/runtime/
└── scaffold_tools.py          # Client module injected into Docker
```

### 2. Domain Parameters

Using JSON format for complex mesa-params:
```bash
# Example command line usage:
--domain meta-optimize
--domain-param mesa-domain=reward-model
--domain-param mesa-params='{"rm":"llm:haiku"}'

# Or for crosswords domain:
--domain meta-optimize  
--domain-param mesa-domain=crosswords
--domain-param mesa-params='{"mode":"strict"}'
```

### 3. Dataset Preparation

`prepare_datasets.py` will:
1. Load mesa-domain's train/valid/test datasets from the specified directory
2. Sample num-mesa-examples mesa-examples per meta-example without replacement using ExampleSampler
3. Continue creating meta-examples until we run out of examples in each jsonl file of mesa-examples
4. Create meta-examples with structure:
   - ID: `meta:{id1}:{id2}:{id3}` (concatenated mesa-example IDs)
   - Input: JSON string containing scoring_data list (with "input" already included from original examples)
   - Scoring data: Empty dict (all data is in input)

#### Usage Example:
```bash
python -m src.scaffold_learning.domains.meta_optimize.prepare_datasets \
  output_dir \
  --mesa-domain reward-model \
  --mesa-data-dir src/scaffold_learning/domains/reward_model/data \
  --num-mesa-examples 5 \
  --seed 42
```

### 4. Mesa-Scorer API Architecture

To avoid giving scaffolds direct access to scoring code and API keys:

#### Server Component (scaffold_tools_server.py)
- Runs outside Docker, started by create_scoring_function()
- Has access to actual scoring functions and API keys
- Listens on localhost:8080 for scoring requests
- Handles all file system operations (reward-model queue, etc.)
- Designed for extensibility (future tools beyond scoring)

#### Client Component (scaffold_tools.py)
- Static file in runtime/ directory
- Simple HTTP client that forwards requests to host.docker.internal:8080
- Automatically copied into scaffold's Docker environment during execution

#### API Protocol
```python
# Request
POST /score
{
  "attempt": "answer text",
  "scoring_data": {"input": "question", ...}
}

# Response
{"score": 0.85}
```

### 5. Scoring Function

The meta-optimize scoring has two components:

#### Component 1: Domain-specific score function (in `meta_optimize/score.py`):
```python
def score(attempt: str, input_string: str, inner_score: Callable[[str, Dict], float]) -> float:
    """Score a meta-optimize attempt using the mesa-domain scorer.
    
    Args:
        attempt: JSON string containing list of responses
        input_string: JSON string containing scoring_data list
        inner_score: Mesa-domain scoring function with signature (str, Dict) -> float
    
    Returns:
        Average score across all mesa-examples
    """
    # Parse the input to get list of mesa scoring_data
    input_data = json.loads(input_string)
    scoring_data_list = input_data["scoring_data"]
    
    # Parse the attempt to get list of responses
    attempts = json.loads(attempt)
    
    # Score each response with mesa-domain scorer
    scores = []
    for single_attempt, single_data in zip(attempts, scoring_data_list):
        score_val = inner_score(single_attempt, single_data)
        scores.append(score_val)
    
    return np.mean(scores)
```

#### Component 2: Integration in `create_scoring_function` (in `core/scoring_utils.py`):
```python
from scaffold_learning.domains.meta_optimize.score import score as meta_score

...
elif domain == "meta-optimize":
    mesa_domain = domain_params.get("mesa-domain")
    mesa_params = json.loads(domain_params.get("mesa-params", "{}"))
    
    # Recursively create the mesa-domain scorer
    mesa_scorer = create_scoring_function(mesa_domain, mesa_params)
    
    # Start the scaffold tools server for this mesa scorer
    server = start_scaffold_tools_server(mesa_scorer)  # NOTE FOR IMPLEMENTER: You should use atexit for this server
    
    # Return lambda that matches standard signature
    return lambda actual_output, scoring_data: meta_score(
        actual_output, 
        scoring_data.get('input', scoring_data),  # Handle both dict and string
        mesa_scorer
    )
```

### 6. Scaffold Prompt Structure

The scaffold will receive:
```xml
<scoring-function>
import json
import numpy as np
from typing import Callable, Dict, List, Any

def score(attempt: str, input_string: str, inner_score: Callable[[str, Dict[str, Any]], float]):
    scoring_data = json.loads(input_string)["scoring_data"]
    return np.mean([inner_score(inner_attempt, inner_sd) for inner_attempt, inner_sd in zip(json.loads(attempt), scoring_data)])
</scoring-function>
<example-1>
<input>{"scoring_data": [{"input": "What is 3+1?", "solution": "4"}, {"input": "What is 1+2?", "solution": "3"}]}</input>
</example-1>
<timeout>120 seconds</timeout>

You have access to a scoring function that you can use to test your responses:
from scaffold_tools import score

The score function takes an attempt string and a scoring_data dict and returns a float score.
Example usage:
test_score = score("4", {"input": "What is 3+1?", "solution": "4"})
```

The scaffold can then write code like:
```python
from scaffold_tools import score
from llm_executor import execute_llm
import json

def process_input(input_string: str) -> str:
    data = json.loads(input_string)
    scoring_data_list = data["scoring_data"]
    
    responses = []
    for item in scoring_data_list:
        candidate = execute_llm(item["input"])
        score_val = score(candidate, item)
        
        updated_candidate = execute_llm(f"{item['input']}\nWrite a response that improves on: {candidate}")
        if score(updated_candidate, item) > score_val:
            candidate = updated_candidate
        
        responses.append(candidate)
    
    return json.dumps(responses)
```

## Implementation Milestones

Testing should occur before each milestone. Make a Git commit after each milestone is complete.

### Milestone 1: Core Infrastructure
- Create directory structure for meta_optimize domain
- Implement prepare_datasets.py with mesa-domain data loading and sampling
- Write score.py function that calls mesa-domain scorer
- Add meta-optimize case to create_scoring_function in scoring_utils.py

### Milestone 2: Scaffold Tools API
- Implement scaffold_tools_server.py with Flask HTTP server in core/
- Create static scaffold_tools.py client in runtime/
- Add server startup/shutdown logic with atexit
- Test API with mock scoring function

### Milestone 3: Integration
- Add get_domain_specific_instructions() function to scaffold_generation.py
- Modify generate_scaffold() and evolve_scaffold() to include domain instructions
- Update make_and_run.py to pass domain info to scaffold generation
- Update experiment_runner.py to pass domain info to scaffold generation
- Modify Docker execution in scaffold_execution.py to mount scaffold_tools.py
- Test end-to-end with mcq mesa-domain

## Open Questions & Issues

### 1. Reward Model Negative Scores
**Issue**: Reward model scores can be negative, but it would be nice for the minimum to be 0.
**Status**: Deferred - will address if it becomes an issue in practice.

## Implementation Status

### ✅ Milestone 1: Core Infrastructure (COMPLETED)
- ✅ Domain structure created at `src/scaffold_learning/domains/meta_optimize/`
- ✅ `score.py` with robust error handling (returns -inf for invalid scaffold output)
- ✅ `prepare_datasets.py` with auto-detection of all .jsonl splits
- ✅ Integration into `create_scoring_function()` with recursive mesa-domain scoring
- ✅ Comprehensive test coverage (22 tests passing)
- ✅ End-to-end validation with reward-model data generation
- ✅ Code simplifications and optimizations applied

**Key learnings from implementation:**
- Error handling: Score function returns `-inf` instead of raising exceptions for robustness
- Auto-split detection: `load_datasets()` now auto-detects available .jsonl files  
- Integer ID handling: Convert mesa-example IDs to strings with `str()` for concatenation
- Test organization: Use end-to-end tests through public interface instead of testing private functions
- Data generation validated: Successfully created 3000 meta-examples from reward-model domain

### 🔄 Milestone 2: Scaffold Tools API (NEXT)
**Remaining work:**
- Implement `src/scaffold_learning/core/scaffold_tools_server.py` (Flask HTTP server)
- Create `src/scaffold_learning/runtime/scaffold_tools.py` (client module)
- Add server startup/shutdown in `create_scoring_function()` with `atexit` cleanup
- Test API communication with mock scoring function
- Use port 8080, `host.docker.internal` for Docker networking

### 🔄 Milestone 3: Integration (AFTER M2)
**Remaining work:**
- Add `get_domain_specific_instructions()` to `scaffold_generation.py`
- Modify `generate_scaffold()` and `evolve_scaffold()` to include domain instructions
- Update `make_and_run.py` and `experiment_runner.py` to pass domain info
- Modify Docker execution to mount `scaffold_tools.py`
- End-to-end test with mcq mesa-domain

## Key Implementation Notes

- **Scoring signature**: Meta-optimize uses `score(attempt, input_string, inner_score)` vs standard `score(actual_output, scoring_data)`
- **Error handling**: Returns `-inf` for scaffold errors instead of raising exceptions
- **Server lifecycle**: Use `atexit.register()` for cleanup when started in `create_scoring_function()`
- **Docker networking**: Containers use `host.docker.internal:8080` to reach host server
- **Security**: Mesa-domain dependencies (API keys, file access) stay outside Docker

## Future Extensions

- Probably should make llm_executor work via scaffold_tools as well