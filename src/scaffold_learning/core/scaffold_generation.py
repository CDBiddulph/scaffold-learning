from typing import List
from datetime import datetime
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldRunData,
    ScaffoldMetadata,
)
from scaffold_learning.core.llm_interfaces import LLMInterface


def extract_python_code(response: str) -> str:
    """Extract Python code from LLM response.

    Args:
        response: Raw LLM response that may contain markdown formatting

    Returns:
        Extracted Python code

    Raises:
        ValueError: If no Python code block is found
    """
    if "```python" in response:
        code = response.split("```python")[1].split("```")[0].strip()
    elif "```" in response:
        code = response.split("```")[1].split("```")[0].strip()
    elif "def process_input" in response:
        # Looks like raw Python code (e.g., from mock interface)
        code = response.strip()
    else:
        raise ValueError("LLM response doesn't contain valid Python code")
    return code


def build_generation_prompt(prompt: str, examples: List[DatasetExample]) -> str:
    """Build the full prompt for scaffold generation.

    Args:
        prompt: Task description
        examples: Training examples to include

    Returns:
        Complete prompt for the scaffolder LLM
    """
    full_prompt = f"{prompt}\n\n"

    for i, example in enumerate(examples, 1):
        full_prompt += f"Example {i}:\n"
        full_prompt += f"Input: {example.input}\n"
        full_prompt += f"Expected output: {example.scoring_data.get('solution', str(example.scoring_data))}\n\n"

    full_prompt += "Write a scaffold.py that implements process_input() to handle inputs like these examples."

    return full_prompt


def get_scaffolder_system_prompt() -> str:
    """Get the system prompt for the scaffolder LLM."""
    # For now, inline the system prompt. In the future, could read from file.
    return """You are a Python code generator. Your task is to write a complete Python script based on the user's requirements.

IMPORTANT CONSTRAINTS:
1. Your script must implement a function called `process_input(input_string: str) -> str`
2. You have access to an executor LLM through a library called 'llm_executor'
3. The llm_executor has a function: execute_llm(prompt, system_prompt="") -> str
4. In your prompts to the executor LLM, be clear about the expected output format
5. Your script should be self-contained and runnable
6. Include proper error handling
7. Make sure your error messages include all information that would help debug the error
8. Use Python's logging module for logging important events, errors, and debug information

Generate a complete, working Python script that solves the user's problem. Do not include any explanation outside the code - only return the Python script."""


def generate_scaffold(
    prompt: str, scaffolder_llm: LLMInterface, examples: List[DatasetExample]
) -> ScaffoldResult:
    """Generate a new scaffold by prompting the scaffolder LLM.

    Args:
        prompt: Task description for what the scaffold should do
        scaffolder_llm: LLM interface to use for generating the scaffold
        examples: Training examples to show the scaffolder

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    full_prompt = build_generation_prompt(prompt, examples)
    system_prompt = get_scaffolder_system_prompt()

    response = scaffolder_llm.generate_response(full_prompt, system_prompt)
    code = extract_python_code(response)

    metadata = ScaffoldMetadata(
        created_at=datetime.now().isoformat(),
        model=None,  # Will be set by the runner
        parent_scaffold_id=None,
        iteration=0,
    )

    return ScaffoldResult(code=code, metadata=metadata)


def improve_scaffold(
    run_data: ScaffoldRunData, scaffolder_llm: LLMInterface
) -> ScaffoldResult:
    """Generate an improved version of a scaffold based on execution feedback.

    Args:
        run_data: Data from previous scaffold execution including logs and score
        scaffolder_llm: LLM interface to use for generation

    Returns:
        ScaffoldResult containing improved code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    prompt = f"""I have a scaffold that needs improvement. Here's the current code:

```python
{run_data.code}
```

When run with this input:
{run_data.example.input}

Expected output:
{run_data.example.scoring_data.get('solution', str(run_data.example.scoring_data))}

The scaffold produced:
{run_data.actual_output}

Execution logs:
{run_data.execution_log}

Score: {run_data.score}

Please improve the scaffold to maximize the score. Focus on producing the expected output.
Write the complete improved scaffold.py code."""

    system_prompt = get_scaffolder_system_prompt()
    response = scaffolder_llm.generate_response(prompt, system_prompt)
    code = extract_python_code(response)

    metadata = ScaffoldMetadata(
        created_at=datetime.now().isoformat(),
        model=None,  # Will be set by the runner
        parent_scaffold_id=None,  # Will be set by the runner
        iteration=1,  # Will be set properly by the runner
    )

    return ScaffoldResult(code=code, metadata=metadata)
