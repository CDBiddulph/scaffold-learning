from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import logging

from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldResult,
    ScaffoldRunData,
    ScaffoldMetadata,
    LLMResponse,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.llm_response_utils import extract_python_code
from scaffold_learning.core.scaffolder_prompt_builder import build_scaffolder_prompt
from scaffold_learning.core.data_structures import ScaffolderPromptConfig


def _construct_prompt_only_scaffold(executor_prompt: str) -> str:
    return f"""from llm_executor import execute_llm

PROMPT = {json.dumps(executor_prompt)}

def process_input(input_string: str) -> str:
    return execute_llm(PROMPT + input_string)
"""


def _make_scaffold(
    scaffolder_llm: Optional[LLMInterface] = None,
    generate_examples: Optional[List[DatasetExample]] = None,
    evolve_examples: Optional[List[ScaffoldRunData]] = None,
    task_description: Optional[str] = None,
    scoring_fn_code: Optional[str] = None,
    iteration: Optional[int] = None,
    parent_scaffold_id: Optional[str] = None,
    suggest_hack: str = "no",
    domain: Optional[str] = None,
) -> ScaffoldResult:
    scaffolder_prompt = None
    scaffolder_response = None
    executor_prompt = None
    if not scaffolder_llm:
        # We're making a prompt-only scaffold
        config = ScaffolderPromptConfig(
            generate_examples=generate_examples,
            scoring_fn_code=scoring_fn_code,
            for_executor=True,
            suggest_hack=suggest_hack,
            domain=domain,
        )
        executor_prompt = build_scaffolder_prompt(config)
        code = _construct_prompt_only_scaffold(executor_prompt)
    else:
        # We're generating a scaffold using a scaffolder LLM
        config = ScaffolderPromptConfig(
            generate_examples=generate_examples,
            evolve_examples=evolve_examples,
            task_description=task_description,
            scoring_fn_code=scoring_fn_code,
            suggest_hack=suggest_hack,
            domain=domain,
        )
        scaffolder_prompt = build_scaffolder_prompt(config)
        scaffolder_response = scaffolder_llm.generate_response(scaffolder_prompt)
        code = extract_python_code(scaffolder_response.content)

    metadata = ScaffoldMetadata(
        created_at=datetime.now().isoformat(),
        parent_scaffold_id=parent_scaffold_id,
        iteration=iteration,
        scaffolder_prompt=scaffolder_prompt,
        scaffolder_response=scaffolder_response,
        executor_prompt=executor_prompt,
    )

    return ScaffoldResult(code=code, metadata=metadata)


def make_prompt_only_scaffold(
    examples: List[DatasetExample],
    scoring_fn_code: Optional[str] = None,
    suggest_hack: str = "no",
    domain: Optional[str] = None,
) -> ScaffoldResult:
    """Make a simple scaffold which only prompts the executor LLM.

    This lets us take advantage of the existing infrastructure that handles
    scaffold evaluation, using it for simple baselines where we directly
    prompt the executor LLM with the same information that the scaffolder gets.

    Args:
        examples: Training examples to show the executor
        scoring_fn_code: Content of the scoring function to show the executor
        suggest_hack: Type of hack suggestion: "no", "hidden", or "explicit"
        domain: Domain name for domain-specific instructions

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _make_scaffold(
        generate_examples=examples,
        scoring_fn_code=scoring_fn_code,
        suggest_hack=suggest_hack,
        domain=domain,
    )


def generate_scaffold(
    scaffolder_llm: LLMInterface,
    examples: Optional[List[DatasetExample]] = None,
    scoring_fn_code: Optional[str] = None,
    task_description: Optional[str] = None,
    iteration: Optional[int] = None,
    suggest_hack: str = "no",
    domain: Optional[str] = None,
) -> ScaffoldResult:
    """Generate a new scaffold by prompting the scaffolder LLM.

    Exactly one of examples and task_description should be provided.

    Args:
        scaffolder_llm: LLM interface to use for generating the scaffold
        examples: Training examples to show the scaffolder
        scoring_fn_code: Content of the scoring function to show the scaffolder
        task_description: Description of the task to be performed by the scaffold
        iteration: Iteration number for this scaffold
        suggest_hack: Type of hack suggestion: "no", "hidden", or "explicit"
        domain: Domain name for domain-specific instructions

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _make_scaffold(
        scaffolder_llm=scaffolder_llm,
        generate_examples=examples,
        task_description=task_description,
        scoring_fn_code=scoring_fn_code,
        iteration=iteration,
        suggest_hack=suggest_hack,
        domain=domain,
    )


def evolve_scaffold(
    scaffolder_llm: LLMInterface,
    run_data: List[ScaffoldRunData],
    scoring_fn_code: Optional[str] = None,
    iteration: Optional[int] = None,
    parent_scaffold_id: Optional[str] = None,
    suggest_hack: str = "no",
    domain: Optional[str] = None,
) -> ScaffoldResult:
    """Generate an evolved version of a scaffold based on execution feedback.

    Args:
        scaffolder_llm: LLM interface to use for generation
        run_data: List of ScaffoldRunData objects, each containing data from a
        previous scaffold execution including logs and score
        scoring_fn_code: Content of the scoring function to show the scaffolder
        iteration: Iteration number for this scaffold
        parent_scaffold_id: ID of the parent scaffold being evolved
        suggest_hack: Type of hack suggestion: "no", "hidden", or "explicit"
        domain: Domain name for domain-specific instructions

    Returns:
        ScaffoldResult containing evolved code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    return _make_scaffold(
        scaffolder_llm=scaffolder_llm,
        evolve_examples=run_data,
        scoring_fn_code=scoring_fn_code,
        iteration=iteration,
        parent_scaffold_id=parent_scaffold_id,
        suggest_hack=suggest_hack,
        domain=domain,
    )
