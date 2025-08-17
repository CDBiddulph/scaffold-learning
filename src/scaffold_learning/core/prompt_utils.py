"""Utilities for building prompts for LLMs."""

from typing import Any, Dict, List, Union

from scaffold_learning.core.data_structures import DatasetExample, ScaffoldRunData
from scaffold_learning.core.xml_utils import dict_to_xml


def format_examples_as_xml(
    examples: List[Union[DatasetExample, ScaffoldRunData]],
) -> str:
    """Format multiple examples as XML.

    Args:
        examples: List of DatasetExample or ScaffoldRunData objects

    Returns:
        XML-formatted string containing all examples

    Raises:
        ValueError: If no examples provided
    """
    if not examples:
        raise ValueError("No examples provided")

    return "\n".join(
        [_format_example_as_xml(example, i) for i, example in enumerate(examples, 1)]
    )


def _format_example_as_xml(
    example: Union[DatasetExample, ScaffoldRunData], idx: int
) -> str:
    """Format a single example as XML.

    Args:
        example: DatasetExample or ScaffoldRunData object
        idx: 1-based index for the example

    Returns:
        XML-formatted string for the example
    """
    dataset_example = (
        example.example if isinstance(example, ScaffoldRunData) else example
    )

    xml_dict = {"input": dataset_example.input}
    # Add scoring data if it exists, generally adding the field "expected_output"
    xml_dict.update(_get_scoring_data_xml_dict(dataset_example.scoring_data))

    if isinstance(example, ScaffoldRunData):
        xml_dict.update(
            {
                "actual_output": example.actual_output,
                "execution_log": example.execution_log,
                "score": example.score,
            }
        )

    return dict_to_xml(xml_dict, f"example-{idx}")


def _get_scoring_data_xml_dict(scoring_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert scoring data to XML-friendly dict.

    Args:
        scoring_data: Dictionary containing scoring information

    Returns:
        Dictionary with expected_output field if applicable

    Raises:
        ValueError: If scoring data has unknown keys
    """
    scoring_data_keys = set(scoring_data.keys())
    if scoring_data_keys == {"input"}:
        return {}  # The prompt already appears in the input field, so don't repeat it
    elif scoring_data_keys == {"input", "solution"}:
        return {"expected_output": scoring_data["solution"]}
    elif scoring_data_keys == {"input", "correct_answer"}:
        return {"expected_output": scoring_data["correct_answer"]}
    elif scoring_data_keys == {"input", "correct_answer", "explanation"}:
        return {"expected_output": scoring_data["correct_answer"]}
    else:
        raise ValueError(f"Unknown scoring data keys: {scoring_data_keys}")
