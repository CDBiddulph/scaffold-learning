# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a research project for LLM-generated script execution, using a "scaffolder LLM" to generate Python scripts that can utilize an "executor LLM".

## Best Practices

### General philosophy
- This is an ongoing, rough research project, NOT a production system
- Focus on velocity and simplicity over "professional" code
- Do NOT worry about backwards compatibility, as this repo has only one user
- Things can change very quickly, so it's often not worth handling every edge case
- However, tests should be sufficient to rule out bugs in mainline code paths

### Code Structure
- Don't import in the middle of a Python file - always import at the top
- Break up large functions - ideally no more than 30 lines
    - Extract validation code, complex logic, etc. into separate functions
- Don't duplicate code - remember DRY
    - Guideline: if ~3 lines of code appear twice, you should probably fix it
    - If your new feature would result in duplicate code, factor the logic into a shared function
- Python scripts should simply pass errors up the call stack most of the time
    - This makes our code much simpler
    - Don't catch errors and continue silently, as this can hide bugs
    - Don't return exit codes in Python CLI scripts, just raise an error
- Write in a style that matches the standard of the "black" Python formatter

### Testing
- When writing tests, don't use or test any private methods
- Add new unit tests to existing files rather than creating ad-hoc test files (test_my_bugfix.py ❌)
- Make unit tests general and useful enough to avoid future regressions
    - Don't add unit tests just for the sake of it, testing trivial aspects of the code
        - If you can't do better than that, it's better not to write a test at all
    - Examples of trivial tests: 
        - Testing that a class constructor sets attributes to the values you passed in
        - Testing that an implementation of a class contains certain functions
- Tests should always be about behavior, not implementation
    - Do not test private methods, mere existence of attributes
- Unit tests shouldn't be redundant - check explicitly for overlap with existing tests
- Avoid `time.sleep` in tests; mock time if needed
- Avoid patching and mocks if possible
    - Do not patch/mock:
        - Files (use temp files instead)
        - Other files within the codebase
            - Unless the file has its own dependency that requires patching/mocking
        - Anything that is deterministic and fast
    - Okay to patch/mock:
        - User input (stdin, input())
        - Time-related functions (time.time, datetime.now)
        - Network calls (HTTP requests, API calls)
        - External system calls (subprocess, os.system)
        - Random number generation
    - Prefer mocking to patching if there's a fairly easy way to do it
        - Consider whether you can use MockLLMInterface from llm_interfaces.py
- Be smart about parameterized tests and factoring out common test pieces
    - You can usually reduce duplication in your tests this way
    - Think about parameterization and deduplication each time you write tests
    - You can even proactively modify existing tests to remove duplication
- Test the full output of functions, not small pieces
    - If assert on pieces, it's hard to understand what the output should actually look like
    - Example: prefer assertEqual to assertIn when testing string outputs
    - Prefer to test the full output in every test case, but at least do it once
    - If the string to test is very long, you can consider using assertIn in all tests but one
- Don't be afraid to write tests that you know are likely incorrect; you can change them later
    - For example, if you're writing a function that shortens a string to exactly 50 characters
        - Don't assert on the length of the string, assert on the exact value of the string!
        - You might not be able to count characters accurately, so the test might fail
        - But give your best guess as to the right value
        - It doesn't matter if it fails, because you will see what the right value is soon
        - As long as the actual output is about the same as your guess, you will see that your code is correct
    - No need to write comments like "this test may fail" - you will fix it soon, so no need for preemptive disclaimers
- Run tests with `pytest`, not `python -m pytest`

### Test-Driven Development (TDD)
Whenever I ask you to implement a new feature, consider whether you can use TDD, and if so, do so.
1. If applicable, write stubs
    - If the task involves writing brand-new class(es), write these classes with stub functions
    - The stub should include a docstring explaining the external behavior in detail, but not the internals
    - The stubs should raise NotImplementedError
    - *Only* write functions that will be used outside this class - that is, public functions
    - Once you're done, explain to me in writing how each function will *call* and *be called* by other classes
        - Do not explain this in the comments, as this information generally does not belong in code
    - Pause and wait for me to confirm that the stubs look good
2. Write failing tests
    - Don't include comments saying something like "this will fail because we're doing TDD"
        - The comments and naming should keep with the style of the other tests in the file
        - We should plan to keep this test around without changes
    - Write the most generic and minimal test possible
        - Don't duplicate the exact scenario where we saw the bug
    - Verify that the tests actually fail
    - Pause and wait for me to confirm that the tests look good
4. Write minimal code that makes the tests pass

### Comments
- Write "timeless" comments
    - Comments are not messages to your current supervisor, they are for future readers
        - You tend to add comments mentioning whatever I just told you to do
        - This usually doesn't make sense from the perspective of future readers
        - The explanation of your work should go in your final response to me, NOT the comments
    - Examples:
        - Bad: "This flag is now required" (assumes reader knows/cares that it wasn't before)
        - Bad: "Added parameter foo" (obviously it was added)
        - Bad: "Test X without patching files" (there's no need to mention what you aren't doing)
        - Good: Comments that explain *why* something exists or *how* it works

### Planning and documentation
- Whenever we start a big new feature, here is what will happen in terms of planning:
    - I give you rough notes on what I want the feature to be
    - You will ask clarifying questions and I will answer them
    - You ask more questions, until you're 100% sure you understand what I want
    - You write down documentation for yourself
    - This documentation will go in a Markdown file: docs/{FEATURE}.md
- Documentation tips
    - Generally, you will only have to write documentation for *yourself* to use
        - The goal is to teach yourself (or a fresh, memory-wiped instance of yourself) all the context you need
    - Don't explain things that are obvious to you from your prior SWE knowledge, only project-specific information
    - However, write down anything that would not be clear to somebody who hadn't heard everything you just heard
    - It's particularly important to write things from our conversation which do NOT appear in the existing docs/code
    - Do not use excessive verbiage
        - For example, "this feature will be crucial for increasing efficiency, saving developer time..." is not helpful
        - Don't use lots of pretty formatting either
            - For instance, a table of contents is totally unnecessary
        - Your documentation should be very practical and dense with information
        - However, if using a concrete example would help get an idea across, feel very free to use one!
    - Imagine looking down from heaven at a young, naive copy of yourself
        - After it reads your documentation, it will start implementing the project, using ONLY that information
        - Do you think "oh no, that copy doesn't know X!"
        - If so, you should make sure that you include X!

### Git Practices
- Don't reference things in commit messages that don't appear in the diff
    - For example:
        - You implement feature X
        - I tell you to remove duplication in your new feature and you remove it
        - You write a commit message saying "Implemented X and removed duplication"
        - This is bad, because the duplication wasn't even part of the original code
        - Your commit message should only talk about how you implemented X

## Commands

### Development Commands
- **Run tests**: `pytest` (runs all tests)
  - Never use `python -m pytest`.
- **Run specific test**: `pytest tests/domains/crosswords/test_score.py::TestScore::test_perfect_across_only`
- **Format code**: `black .`

### Core Scaffold Commands
- **Generate scaffold**: `generate-scaffold "prompt describing what script should do" --scaffold-name my-scaffold`
- **Run scaffold**: `run-scaffold scaffold-name "input string"`
- **Run scaffold with file input**: `run-scaffold scaffold-name --file input.txt`
- **Override model**: `run-scaffold scaffold-name "input" --model gpt-4o`

### Crossword Domain Commands
- **Download puzzles**: `python -m src.scaffold_learning.domains.crosswords.download_puz output_dir -n 10`
- **Prepare datasets**: `python -m src.scaffold_learning.domains.crosswords.prepare_datasets --num-train 50 --num-valid 50 data_dir`
- **Score crossword solutions**: `python -m src.scaffold_learning.domains.crosswords.score expected.jsonl attempted.txt --puzzle NY_Times_2025_04_24`

## Architecture

### Core Components

**LLM Interfaces** (`src/scaffold_learning/core/llm_interfaces.py`):
- `LLMInterface`: Abstract base class for all LLM providers
- `OpenAIInterface`: Handles OpenAI GPT models
- `AnthropicInterface`: Handles Anthropic Claude models  
- `HumanInterface`: Interactive human input/output
- `MockInterface`: For testing
- `LLMFactory`: Creates appropriate LLM instances based on model specifications

**Scaffold Execution** (`src/scaffold_learning/cli/run_scaffold.py`):
- Executes generated scripts in Docker containers for isolation
- Handles real-time output streaming and timeout management
- Supports both LLM and human executors with different execution modes
- Logs all executions with structured JSON + text format in `logs/scaffold_name/`

**Script Generation** (`src/scaffold_learning/cli/generate_scaffold_script.py`):
- Uses scaffolder LLM to generate Python scripts based on prompts
- Creates scaffold directories with `scaffold.py`, `llm_executor.py`, `llm_interfaces.py`, and `metadata.json`
- Supports model overrides and API key configuration

### Docker Architecture
- All scaffold execution happens in Docker containers for security/isolation
- Container includes Python environment with LLM interfaces and dependencies
- Volumes mount scaffold code and logs directory
- Environment variables pass API keys and model specifications

### Crossword Domain

The crosswords domain (`src/scaffold_learning/domains/crosswords/`) implements a complete crossword puzzle processing pipeline:

**Key Modules**:
- `puz.py`: Crossword puzzle file format parser (.puz files)
- `puzzle_utils.py`: Shared utilities for downloading, converting, and processing puzzles
- `download_puz.py`: Downloads puzzles from GitHub archive to .puz files
- `prepare_datasets.py`: Converts puzzles to JSONL format for ML training
- `score.py`: Scores crossword solutions with strict/lenient modes
- `save_puz.py`: Saves puzzles as text files (input/solution formats)

**Data Flow**:
1. `download_puz.py` fetches puzzles from GitHub archive → saves as .puz files
2. `prepare_datasets.py` converts .puz files → train.jsonl/valid.jsonl datasets  
3. `score.py` evaluates solutions against expected answers

**Scoring System**:
- **Strict mode**: Square is correct only if ALL instances (grid, across, down) are correct
- **Lenient mode**: Square is correct if ANY instance is correct
- Supports multiple input formats: grid format, clue-answer format, or mixed
- Clue numbering follows standard crossword conventions (numbered squares that start words)

### Scaffold Script Structure

Generated scaffolds follow this pattern:
```
scaffold-scripts/scaffold-name/
├── scaffold.py          # Main processing logic with process_input() function
├── llm_executor.py      # LLM execution utilities  
├── llm_interfaces.py    # LLM interface implementations
└── metadata.json        # Scaffold configuration
```

**Key Functions**:
- `process_input(input_string) -> str`: Main entry point that all scaffolds must implement
- `execute_llm(prompt, system_prompt="")`: Utility for calling executor LLM

### Model Specifications

The framework uses a unified model specification format:
- `gpt-4o`, `gpt-4.1-nano` → OpenAI models
- `sonnet`, `haiku` → Anthropic models  
- `mock` → Mock interface for testing
- `human/human` → Interactive human interface

API keys are loaded from `.env` file or environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

### Logging and Output

**Execution Logs** (`logs/scaffold_name/YYYYMMDD_HHMMSS.log`):
- Structured format with input, output, stderr, and metadata
- Real-time streaming during execution
- Separate JSON files with structured data

**Timeout Handling**:
- Default 2-minute timeout for LLM scaffolds
- No timeout for human scaffolds (interactive mode)
- Graceful shutdown with partial output capture

## Testing

Tests are organized by domain:
- `tests/cli/`: CLI component tests
- `tests/domains/`: Domain-specific functionality tests
