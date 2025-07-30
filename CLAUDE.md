# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a research project for LLM-generated script execution, using a "scaffolder LLM" to generate Python scripts that can utilize an "executor LLM".

## Best Practices

### General philosophy
- This is an ongoing, rough research project, NOT a production system
- Focus on velocity and simplicity over "professional" code
- NEVER TRY TO MAINTAIN BACKWARDS COMPATIBILITY
    - I am the only user of this repo, and I have no desire to maintain multiple ways of doing the same thing
    - If you find yourself thinking "we should keep this backwards compatible by..." STOP THAT
    - "Breaking existing behavior" is fine
    - Anti-patterns to AVOID
        - Adding optional parameters with defaults to preserve old behavior
        - Creating `_v2` or `_new` versions of functions
        - Adding feature flags or config options to toggle between old/new behavior
        - Writing code like "if legacy_mode:" or "for backwards compatibility"
- Things can change very quickly, so it's often not worth writing code to handle every edge case
    - However, tests should be sufficient to rule out bugs in mainline code paths
- Generally, stick to the stated plan
    - However, it's possible that problems will only become clear as you implement
    - If in doubt, *stop* and ask me what to do
- If I ask you a question or express doubt, that doesn't mean you're wrong
    - Stick to your guns when it counts, don't always fold to anything I say!
    - I often lack the context that you have, on the ground writing code; sometimes I'm just completely off-base
    - Often, I'm just asking a question for my own personal understanding
    - NEVER start your answer with "You're absolutely right!"
        - Instead, explicitly write out why I might be right, then why you might be right, then a balanced conclusion

### Code Structure and Style
- Don't import in the middle of a Python file - always import at the top
- Break up large functions - ideally no more than 30 lines
    - Extract validation code, complex logic, etc. into separate functions
- Break up large files - ideally no more than 500 lines
    - Move classes into their own files
- Don't duplicate code - remember DRY
    - Guideline: if ~3 lines of code appear twice, you should probably fix it
    - If your new feature would result in duplicate code, factor the logic into a shared function
- Python scripts should simply pass exceptions up the call stack
    - NEVER catch exceptions, as this can hide bugs
        - Because this is a research project, it doesn't matter if our experiments crash
            - It is far more valuable to see that there is an error, even if we sometimes get false positives
        - Occasionally, it's actually appropriate to catch an exception and log a clear warning
            - However, if you feel like you actually should do this, you MUST STOP and ask for my explicit approval
    - Don't return exit codes in Python CLI scripts, only raise an error
        - This is simpler and more Pythonic
- Flags should use --hyphens-between-words-like-this.
    - Even if I accidentally tell you to make a --flag_like_this, turn it into a --flag-like-this
- Lean towards using dataclasses rather than tuples or dictionaries, especially for public interfaces 
    - If a dataclass will be used across multiple files, consider putting it in its own file
        - This helps avoid circular import errors
        - It can be fine to put it in the same file as other dataclasses/enums
- Getting names right is very important
    - They should be relatively short, but unambiguous
    - For example, when naming a new dataclass, think about whether it will be very clear what it does
- Avoid "magic" values
    - E.g. string literals should appear as constants at the top of the file, especially if they appear multiple times
- If an argument can be None, remember to write its type as Optional[...]
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
- Before telling me you're done, remember to run `pytest` to run ALL tests.
    - Running only a subset of tests is unnecessary unless you're working on debugging just one test
    - It's best to run all tests with `pytest` to avoid missing failing tests

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
        - Each individual question should be numbered, so that I can reference it easily in my response
        - Include questions about the future of the code, *after* this feature is implemented
            - This helps you understand where you need to make your code flexible/extensible
            - This may be useful for you to know during implementation, so mention them your documentation
            - To be clear, you should not try to implement things from these future plans I describe
                - Unless it's very easy to do in the course of implementation
                - E.g. making a field a list from the start is probably worth it, even if the value is singular for now
        - Give your best guess as to the answer, and if correct, I will confirm your guess with "c" for correct
        - Be specific in your guess, even if you think it's probably wrong
            - If I like your guess and confirm that we should use it, that saves us both time
        - Don't be afraid to ask dumb questions, point out big-picture flaws in my idea, or note your confusion
    - You ask more questions, until you're 100% sure you understand what I want
        - Don't be afraid to continue asking questions, even if it seems like I want you to move on
    - Then, tell me a full implementation plan
        - This plan should include any parts that I didn't fully specify
            - It should focus on the implementation details, whereas my spec to you focused more on high-level goals
            - You should *explicitly* write the following sections:
                - What files you will create/modify
                    - List all new/modified/deleted classes, including dataclasses
                        - List the new/modified/deleted public methods (even the ones that aren't in a class)
                            - For each method, include the following information:
                                - Full method stub
                                    - Function signature
                                        - Looks like `function_name(arg1: type1, ...`
                                        - Include full types - `Callable[[int], str]` rather than `callable`
                                    - Docstring
                                        - A detailed description of behavior
                                        - `Args:` with a description of each argument
                                        - `Returns:` and `Raises:` if applicable
                                - Where the method will be called
                                    - Only mention the *public* class or function
                                    - This should include *existing* locations as well as new ones, when applicable
                                    - If it makes it clearer, explain what the method will be used for at each location
                                    - The method should not be called by its own class
                                        - This ensures that the method is actually fit for being public, not private
                    - Give an estimate of the lines of code in the file after you're done
                        - If the file already exists, mention how many lines there currently are
                        - If the file will be more than 500 lines of code, that's okay, but acknowledge this
                - What external libraries/frameworks you will use, if any
                - What existing code from this codebase you will reuse
                    - Where you will reuse it
                    - Whether you will be able to use the code as written
                        - Or if you will instead have to modify the code/factor out parts
                        - How will you do this?
                            - Will you create new utils files? Make private functions public? Etc.
                    - This may require searching through the codebase if you haven't already done so
                - What tests you will create
                    - Including unit and/or integration tests and what behaviors they test
                - Things not covered by the above
                    - Anything else that you think should go in an implementation plan that you didn't already mention
                    - Give a reasonably detailed explanation of how you will do it, don't just say that you will do it
        - The plan should also include a series of milestones in the order you want to implement them
            - Each milestone should start with writing/rewriting tests, since we are doing TDD
            - Not counting bullet points about tests, there should be anywhere from 2-6 bullet points per milestone
        - Ask any questions that you thought of when writing the implementation plan
        - I will confirm whether the plan looks good, or ask you to make modifications
    - You write down documentation for yourself about how to implement the feature
        - This must contain *everything* you just told me in the implementation plan
        - Also include all other information that you think will help you implement this (see "documentation tips")
        - This documentation will go in a Markdown file: docs/{FEATURE}.md
        - Once you're done, explicitly ask yourself whether you missed anything
            - If so, dive back in and add more content
            - Continue asking yourself whether you're done until you're sure you included all the relevant information
    - I will continue to ask for changes in your documentation until I'm happy with it
    - I completely clear your memory
    - I tell your copy to start implementing the plan based on your documentation
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
- **Run experiment**: `run-experiment experiment-name data_dir --domain crosswords --scaffolder-model gpt-4o --executor-model gpt-4 --num-iterations 3`

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
- `HumanLLMInterface`: Interactive human input/output
- `MockLLMInterface`: For testing
- `LLMFactory`: Creates appropriate LLM instances based on model specifications

**Scaffold Execution** (`src/scaffold_learning/cli/run_scaffold.py`):
- Executes generated scripts in Docker containers for isolation
- Handles real-time output streaming and timeout management
- Supports both LLM and human executors with different execution modes
- Logs all executions with structured JSON + text format in `logs/scaffold_name/`

**Script Generation** (`src/scaffold_learning/cli/generate_scaffold.py`):
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
