from typing import Any, Dict, List
from datetime import datetime

from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldRunData,
    ScaffoldMetadata,
)
from scaffold_learning.core.llm_interfaces import LLMInterface

_SCAFFOLDER_INSTRUCTIONS = """Your task is to write a Python scaffold that maximizes its score on held-out examples.

Basic code template:
```python
import logging
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Starting to process input")
    
    try:
        # Your logic here - you can call execute_llm() as needed
        return execute_llm("Your prompt here")
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}", exc_info=True)
        raise
```

Tips:
1. Your script must implement a function called `process_input(input_string: str) -> str`
2. You have access to an executor LLM through a library called `llm_executor`
3. The llm_executor has a function: execute_llm(prompt: str, system_prompt: Optional[str] = None) -> str
4. Your script should be self-contained and runnable
5. Avoid bloated or disorganized code
6. Include proper error handling
7. Make sure your error messages include all information that would help debug the error
8. Use Python's logging module for logging important events, errors, and debug information
9. Enclose your code in ```python tags

Based on the scaffold's output, you will get a score from 0 to 1.
In the example(s) above, returning <expected-output> would get you a score of 1.
Your code will automatically get a score of 0 if it takes any more than <timeout> seconds to run, so you may want to implement measures to ensure that it stops before that point."""

_EVOLUTION_EXTRA_INSTRUCTIONS = """There is an attempted Python scaffold in <code>.
You can use this scaffold as a reference or write something completely different.
You can see the output of <code> in <actual-output> and its execution log in <execution-log>.
Finally, you can see the score assigned to <actual-output> in <score>."""


def _extract_python_code(response: str) -> str:
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
    else:
        raise ValueError("LLM response doesn't contain valid Python code")
    return code


def _get_xml(root_tag: str, inner_tags: Dict[str, str]) -> str:
    middle = "\n".join(
        [f"    <{tag}>{value}</{tag}>" for tag, value in inner_tags.items()]
    )
    return f"<{root_tag}>\n{middle}\n</{root_tag}>"


def _get_expected_output(scoring_data: Dict[str, Any]) -> str:
    # TODO: make printing scoring data vary depending on the domain
    # Possibly just have this as a fixed field in the jsonl for simplicity
    return scoring_data["solution"]


def _get_example_xml(example: DatasetExample | ScaffoldRunData, idx: int) -> str:
    if isinstance(example, ScaffoldRunData):
        xml_dict = {
            "input": example.example.input,
            "expected_output": _get_expected_output(example.example.scoring_data),
            "actual_output": example.actual_output,
            "execution_log": example.execution_log,
            "score": example.score,
        }
    else:
        xml_dict = {
            "input": example.input,
            "expected_output": _get_expected_output(example.scoring_data),
        }

    return _get_xml(f"example-{idx}", xml_dict)


def _get_examples_xml(examples: List[DatasetExample | ScaffoldRunData]) -> str:
    if not examples:
        raise ValueError("No examples provided")

    return "\n".join(
        [_get_example_xml(example, i) for i, example in enumerate(examples, 1)]
    )


def _build_prompt(
    examples: List[DatasetExample | ScaffoldRunData], is_evolution: bool
) -> str:
    """Build the full prompt for scaffold generation or evolution.

    Args:
        examples: List of DatasetExample or ScaffoldRunData objects
        is_evolution: If True, the prompt will be for evolution, otherwise it will be for generation

    Returns:
        Complete prompt for the scaffolder LLM
    """
    full_prompt = ""

    # If evolving an existing scaffold, include the code in the prompt
    if is_evolution:
        if not examples or not isinstance(examples[0], ScaffoldRunData):
            raise ValueError("Evolution requires a list of ScaffoldRunData objects")
        code = examples[0].code
        full_prompt = f"<code>```python\n{code}\n```</code>\n"

    # Include the timeout
    timeout_seconds = 120  # TODO: make this configurable
    full_prompt += f"<timeout>{timeout_seconds}</timeout>\n"

    # Include the example data for each example
    full_prompt += _get_examples_xml(examples)

    # Add the shared instructions
    full_prompt += f"\n\n{_SCAFFOLDER_INSTRUCTIONS}"

    # Add the instructions that are specific to evolution
    if is_evolution:
        full_prompt += f"\n{_EVOLUTION_EXTRA_INSTRUCTIONS}"

    return full_prompt


def _generate_or_evolve_scaffold(
    scaffolder_llm: LLMInterface,
    examples: List[DatasetExample | ScaffoldRunData],
    is_evolution: bool,
) -> ScaffoldResult:
    prompt = _build_prompt(examples, is_evolution)

    response = scaffolder_llm.generate_response(prompt)
    code = _extract_python_code(response)

    metadata = ScaffoldMetadata(
        created_at=datetime.now().isoformat(),
        model=None,  # Will be set by the runner
        parent_scaffold_id=None,  # Will be set by the runner
        iteration=0,
        scaffolder_prompt=prompt,
        scaffolder_output=response,
    )

    return ScaffoldResult(code=code, metadata=metadata)


def generate_scaffold(
    examples: List[DatasetExample], scaffolder_llm: LLMInterface
) -> ScaffoldResult:
    """Generate a new scaffold by prompting the scaffolder LLM.

    Args:
        scaffolder_llm: LLM interface to use for generating the scaffold
        examples: Training examples to show the scaffolder

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _generate_or_evolve_scaffold(scaffolder_llm, examples, is_evolution=False)


def evolve_scaffold(
    run_data: List[ScaffoldRunData], scaffolder_llm: LLMInterface
) -> ScaffoldResult:
    """Generate an evolved version of a scaffold based on execution feedback.

    Args:
        run_data: List of ScaffoldRunData objects, each containing data from a
        previous scaffold execution including logs and score
        scaffolder_llm: LLM interface to use for generation

    Returns:
        ScaffoldResult containing evolved code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _generate_or_evolve_scaffold(scaffolder_llm, run_data, is_evolution=True)
