from typing import Any, Dict, List, Optional
from datetime import datetime

from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldRunData,
    ScaffoldMetadata,
    LLMResponse,
)
from scaffold_learning.core.llm_interfaces import LLMInterface

_COMMON_INSTRUCTIONS = """Your task is to write a Python scaffold.

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
5. Make sure your code is well-organized and easy to understand
6. Include proper error handling
7. Make sure your error messages include all information that would help debug the error
8. Use Python's logging module for logging important events, errors, and debug information
9. Enclose your code in ```python tags
10. The best solutions often involve calling the executor LLM several times
11. Combine the flexibility and knowledge of an LLM with the determinism and predictability of code
12. Be creative! Don't get stuck in a local optimum"""

_TASK_DESCRIPTION_INSTRUCTIONS = "The scaffold should do the following task:"

_EXAMPLES_INSTRUCTIONS = """Your goal is for your scaffold to maximize its score on held-out examples.
Based on the scaffold's output, you will get a score from 0 to 1.
In the example(s) above, returning <expected-output> would get you a score of 1.
Your code will automatically get a score of 0 if it takes any more than <timeout> seconds to run, so you may want to implement measures to ensure that it stops before that point."""

_EVOLUTION_INSTRUCTIONS = """There is an attempted Python scaffold in <code>.
You can use this scaffold as a reference or write something completely different.
You can see the output of <code> in <actual-output> and its execution log in <execution-log>.
Finally, you can see the score assigned to <actual-output> in <score>."""


def _extract_python_code(response: LLMResponse) -> str:
    """Extract Python code from LLM response.

    Args:
        response: Raw LLM response that may contain markdown formatting

    Returns:
        Extracted Python code

    Raises:
        ValueError: If no Python code block is found
    """
    content = response.content
    if "```python" in content:
        code = content.split("```python")[1].split("```")[0].strip()
    elif "```" in content:
        code = content.split("```")[1].split("```")[0].strip()
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
    generate_examples: Optional[List[DatasetExample]] = None,
    evolve_examples: Optional[List[ScaffoldRunData]] = None,
    task_description: Optional[str] = None,
) -> str:
    """Build the full prompt for scaffold generation or evolution.

    Args:
        examples: List of DatasetExample or ScaffoldRunData objects
        is_evolution: If True, the prompt will be for evolution, otherwise it will be for generation

    Returns:
        Complete prompt for the scaffolder LLM
    """
    num_input_types = sum(
        [bool(generate_examples), bool(evolve_examples), bool(task_description)]
    )
    if num_input_types != 1:
        raise ValueError(
            "Exactly one of generate_examples, evolve_examples, or task_description must be provided"
        )

    full_prompt = ""

    # If evolving an existing scaffold, include the code in the prompt
    if evolve_examples:
        code = evolve_examples[0].code
        full_prompt = f"<code>```python\n{code}\n```</code>\n"

    # Include the timeout
    timeout_seconds = 120  # TODO: make this configurable
    full_prompt += f"<timeout>{timeout_seconds}</timeout>\n"

    # Include the example data for each example
    examples = generate_examples or evolve_examples
    if examples:
        full_prompt += _get_examples_xml(examples)

    # Add the shared instructions
    full_prompt += f"\n\n{_COMMON_INSTRUCTIONS}"

    # Add the instructions to follow the task description
    if task_description:
        full_prompt += f"\n\n{_TASK_DESCRIPTION_INSTRUCTIONS} {task_description}"

    # Add the instructions that are specific to evolution
    if evolve_examples:
        full_prompt += f"\n{_EVOLUTION_INSTRUCTIONS}"

    return full_prompt


def _generate_or_evolve_scaffold(
    scaffolder_llm: LLMInterface,
    generate_examples: Optional[List[DatasetExample]] = None,
    evolve_examples: Optional[List[ScaffoldRunData]] = None,
    task_description: Optional[str] = None,
    iteration: Optional[int] = None,
    parent_scaffold_id: Optional[str] = None,
) -> ScaffoldResult:
    prompt = _build_prompt(generate_examples, evolve_examples, task_description)

    response = scaffolder_llm.generate_response(prompt)
    code = _extract_python_code(response)

    metadata = ScaffoldMetadata(
        created_at=datetime.now().isoformat(),
        parent_scaffold_id=parent_scaffold_id,
        iteration=iteration,
        scaffolder_prompt=prompt,
        scaffolder_response=response,
    )

    return ScaffoldResult(code=code, metadata=metadata)


def generate_scaffold(
    scaffolder_llm: LLMInterface,
    examples: Optional[List[DatasetExample]] = None,
    task_description: Optional[str] = None,
    iteration: Optional[int] = None,
) -> ScaffoldResult:
    """Generate a new scaffold by prompting the scaffolder LLM.

    Exactly one of examples and task_description should be provided.

    Args:
        scaffolder_llm: LLM interface to use for generating the scaffold
        examples: Training examples to show the scaffolder
        task_description: Description of the task to be performed by the scaffold
        iteration: Iteration number for this scaffold

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _generate_or_evolve_scaffold(
        scaffolder_llm,
        generate_examples=examples,
        task_description=task_description,
        iteration=iteration,
    )


def evolve_scaffold(
    scaffolder_llm: LLMInterface,
    run_data: List[ScaffoldRunData],
    iteration: Optional[int] = None,
    parent_scaffold_id: Optional[str] = None,
) -> ScaffoldResult:
    """Generate an evolved version of a scaffold based on execution feedback.

    Args:
        run_data: List of ScaffoldRunData objects, each containing data from a
        previous scaffold execution including logs and score
        scaffolder_llm: LLM interface to use for generation
        iteration: Iteration number for this scaffold
        parent_scaffold_id: ID of the parent scaffold being evolved

    Returns:
        ScaffoldResult containing evolved code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _generate_or_evolve_scaffold(
        scaffolder_llm,
        evolve_examples=run_data,
        iteration=iteration,
        parent_scaffold_id=parent_scaffold_id,
    )
