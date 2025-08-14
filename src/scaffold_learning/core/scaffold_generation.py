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
    config: ScaffolderPromptConfig,
    scaffolder_llm: Optional[LLMInterface] = None,
    iteration: Optional[int] = None,
    parent_scaffold_id: Optional[str] = None,
) -> ScaffoldResult:
    scaffolder_prompt = None
    scaffolder_response = None
    executor_prompt = None
    if config.for_executor:
        # We're making a prompt-only scaffold
        executor_prompt = build_scaffolder_prompt(config)
        code = _construct_prompt_only_scaffold(executor_prompt)
    else:
        # We're generating a scaffold using a scaffolder LLM
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
    config: ScaffolderPromptConfig,
) -> ScaffoldResult:
    """Make a simple scaffold which only prompts the executor LLM.

    This lets us take advantage of the existing infrastructure that handles
    scaffold evaluation, using it for simple baselines where we directly
    prompt the executor LLM with the same information that the scaffolder gets.

    Args:
        config: Configuration containing all prompt parameters

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    config.for_executor = True
    return _make_scaffold(config=config)


def generate_scaffold(
    config: ScaffolderPromptConfig,
    scaffolder_llm: Optional[LLMInterface] = None,
    iteration: Optional[int] = None,
) -> ScaffoldResult:
    """Generate a new scaffold using configuration.

    Args:
        config: Configuration containing all prompt parameters
        scaffolder_llm: LLM interface to use for generating the scaffold
        iteration: Iteration number for this scaffold

    Returns:
        ScaffoldResult containing code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    assert not config.for_executor
    return _make_scaffold(
        config=config,
        scaffolder_llm=scaffolder_llm,
        iteration=iteration,
    )


def evolve_scaffold(
    config: ScaffolderPromptConfig,
    scaffolder_llm: LLMInterface,
    iteration: Optional[int] = None,
    parent_scaffold_id: Optional[str] = None,
) -> ScaffoldResult:
    """Generate an evolved version of a scaffold based on execution feedback.

    Args:
        config: Configuration containing all prompt parameters including evolve_examples
        scaffolder_llm: LLM interface to use for generation
        iteration: Iteration number for this scaffold
        parent_scaffold_id: ID of the parent scaffold being evolved

    Returns:
        ScaffoldResult containing evolved code and metadata

    Raises:
        ValueError: If LLM response doesn't contain valid Python code
    """
    assert not config.for_executor
    return _make_scaffold(
        config=config,
        scaffolder_llm=scaffolder_llm,
        iteration=iteration,
        parent_scaffold_id=parent_scaffold_id,
    )
