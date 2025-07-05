# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Scaffold Learning is a framework for LLM-generated script execution that uses a "scaffolder LLM" to generate Python scripts that can utilize an "executor LLM". The framework supports multiple LLM providers (OpenAI, Anthropic) and includes special handling for human interaction.

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
