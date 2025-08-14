# Strategy Integration: Remaining Work

## Current Status

Strategy generation infrastructure is complete:

✅ **Core Implementation**:
- `ScaffolderPromptConfig` with strategy field
- `generate_strategies()` function using full scaffolder prompt context
- Updated scaffold generation API to use config pattern
- Strategy inclusion in prompts with "Follow this implementation strategy:" prefix
- Basic CLI integration in make-and-run

✅ **Testing**:
- Comprehensive strategy generation tests (7 test cases)
- Updated scaffold generation tests (14 test cases) 
- Scaffolder prompt builder tests including strategy verification

## Missing: run-experiment Integration

The main missing piece is integrating strategy generation into `run-experiment`. This requires:

### 1. Add Strategy CLI Arguments
Add to `run_experiment.py`:
- `--strategy-model MODEL` - LLM to use for strategy generation
- `--num-strategies N` - Number of strategies to generate (default 1)
- `--human-strategy "text"` - Use provided strategy instead of generating

### 2. Strategy Generation in Experiment Pipeline
- Generate strategies before creating initial scaffolds
- Use different strategies for different scaffold variants
- **Important**: Only use strategies for initial scaffold generation, NOT for evolution
- Evolution should continue using the current approach without strategies

### 3. Update Experiment Configuration
Likely need to:
- Add strategy fields to experiment config dataclass
- Update validation logic
- Ensure strategy information is logged with experiment metadata

### 4. Implementation Approach
```python
# Pseudo-code for integration
if args.strategy_model:
    strategies = generate_strategies(
        llm=create_llm(args.strategy_model),
        scaffolder_prompt_config=base_config,
        num_strategies=args.num_strategies
    )
    # Use strategies[i] for scaffold i
```

### 5. Testing Requirements
- Test strategy integration in experiment pipeline
- Verify evolution still works without strategies
- Test experiment logging includes strategy information
- Validate CLI argument combinations

## Design Constraints

1. **Keep evolution simple**: Strategies only for initial generation
2. **Maintain existing behavior**: Default behavior unchanged when strategies not used
3. **Clean separation**: Strategy generation separate from scaffold evolution logic

## Files to Modify

- `src/scaffold_learning/cli/run_experiment.py` - Main integration
- Likely experiment config dataclass (wherever that lives)
- `tests/cli/test_run_experiment.py` - Test coverage

## Estimated Scope

Small-medium task. The infrastructure exists, just need to wire it into the experiment CLI and ensure proper argument handling/validation.