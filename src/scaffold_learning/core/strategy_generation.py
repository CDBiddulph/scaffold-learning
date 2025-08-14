"""Generate diverse problem-solving strategies for scaffold creation."""

import logging
import json
from typing import List, Dict

from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.llm_response_utils import extract_json_dict
from scaffold_learning.core.data_structures import ScaffolderPromptConfig
from scaffold_learning.core.scaffolder_prompt_builder import build_scaffolder_prompt


_STRATEGY_INSTRUCTIONS = """Your job is to create strategies for scaffolder LLMs. The full prompt that will be sent to the scaffolder LLMs is shown above. Please generate diverse strategies, ready to be inserted in place of "YOUR STRATEGY HERE" in that prompt. Each strategy will be sent to a different scaffolder LLM, which will then implement a scaffold based on that strategy.

Each strategy should describe a different approach or methodology for solving the problem. The strategies should provide specific guidance on how to approach the problem.

Your score will be the maximum score achieved by any generated scaffold. Therefore, it doesn't matter if some of your strategies end up failing, as long as at least one is very successful. However, you shouldn't use a strategy unless you think it has a chance of being the best one. Act like a shrewd investor who knows when to diversify their portfolio and when to commit. (You're different from a traditional investor in that you're not trying to maximize your overall return on investment, but rather the return of your single best bet.)

Each strategy should contain clear instructions providing comprehensive guidance on how to implement the scaffold. Each scaffolder LLM will see the prompt above and a single strategy from your list; they won't see the other strategies you generated, so each strategy must be self-contained and complete.

# JSON format

Return your strategies as a JSON string with two fields: "placeholders" and "strategies", like this:
{{
  "placeholders": {{
    "BASIC_STRATEGY": "Use a basic strategy.",
    "FOO": "You should foo, and this is how.",
    "BAR": "You should bar, and this is how."
  }},
  "strategies": {{
    "0-basic": "$BASIC_STRATEGY Other than that, do whatever you want.",
    "1-foo": "$BASIC_STRATEGY $FOO",
    "2-bar": "$BASIC_STRATEGY $BAR",
    "3-foo-bar": "$BASIC_STRATEGY $FOO $BAR",
    "4-no-basic-strategy": "Do whatever you want."
  }}
}}

The output must be a simple valid JSON string; don't try to construct it using Python. Each key in "placeholders" is a string that can be used as a shortcut to insert common text into "strategies". This is useful, because strategies may often overlap significantly in content. Each strategy key should start with an integer representing the 0-indexed ID of the strategy, and the rest of the key can be any text that's useful for you.

In the example above, "3-foo-bar" will resolve to the strategy "Use a basic strategy. You should foo, and this is how. You should bar, and this is how." The only way to show the scaffolder LLM the value of the placeholder "PLACEHOLDER_NAME" is if you write "$PLACEHOLDER_NAME" in your strategy. The placeholder key will be exactly replaced by the value of the placeholder, so don't write something like "Use the instructions in $FOO to foo". This would produce the ungrammatical strategy "Use the instructions in You should foo, and this is how. to foo".

The example above is designed to showcase how to use placeholders, so it's not necessarily a good example of how to write strategies."""


def _build_strategy_prompt(
    scaffolder_prompt_config: ScaffolderPromptConfig,
    num_strategies: int,
) -> str:
    """Build prompt for strategy generation.

    Args:
        scaffolder_prompt_config: Full scaffolder config
        num_strategies: Number of strategies to generate

    Returns:
        Complete prompt for the LLM
    """
    # Create a copy of the config with "YOUR STRATEGY HERE" placeholder
    config_with_placeholder = ScaffolderPromptConfig(
        generate_examples=scaffolder_prompt_config.generate_examples,
        evolve_examples=scaffolder_prompt_config.evolve_examples,
        task_description=scaffolder_prompt_config.task_description,
        scoring_fn_code=scaffolder_prompt_config.scoring_fn_code,
        strategy="YOUR STRATEGY HERE",
        for_executor=scaffolder_prompt_config.for_executor,
        suggest_hack=scaffolder_prompt_config.suggest_hack,
        domain=scaffolder_prompt_config.domain,
    )

    # Build the scaffolder prompt with the placeholder
    scaffolder_prompt_template = build_scaffolder_prompt(config_with_placeholder)

    prompt = f"""{scaffolder_prompt_template}

---

{_STRATEGY_INSTRUCTIONS}

Generate {num_strategies} strategies, indexed from 0 to {num_strategies-1}."""

    return prompt


def _log_response_content(placeholders: Dict[str, str], strategies: Dict[str, str]):
    """Log JSON content to the console."""
    logging.info("Strategy placeholders:")
    for k, v in placeholders.items():
        logging.info(f"{k}: {json.dumps(v)}")
    logging.info("Strategies:")
    for k, v in strategies.items():
        logging.info(f"{k}: {json.dumps(v)}")


def _parse_numbered_strategies(response: str) -> List[str]:
    """Parse numbered JSON strategies from LLM response.

    Args:
        response: Raw LLM response containing JSON strategies

    Returns:
        List of strategy strings in order

    Raises:
        ValueError: If response doesn't contain valid JSON strategies
    """
    # Use shared JSON extraction utility
    json_dict = extract_json_dict(response)

    # Handle new format with placeholders and strategies fields
    if "strategies" not in json_dict:
        raise ValueError(f"No strategies found in JSON:\n{json_dict}")

    placeholders = json_dict.get("placeholders", {})
    strategies_dict = json_dict["strategies"]

    # Log the placeholders and strategies
    _log_response_content(placeholders, strategies_dict)

    # Extract and resolve placeholders in strategies
    strategies = []
    for strategy_text in strategies_dict.values():
        if not isinstance(strategy_text, str):
            raise ValueError(
                f"Expected string strategy but got {type(strategy_text).__name__}: {strategy_text}"
            )

        # Replace placeholders with their values
        resolved_strategy = strategy_text
        for placeholder_name, placeholder_value in placeholders.items():
            placeholder_ref = f"${placeholder_name}"
            resolved_strategy = resolved_strategy.replace(
                placeholder_ref, placeholder_value
            )

        strategies.append(resolved_strategy)

    if not strategies:
        raise ValueError(f"No strategies found in JSON:\n{json_dict}")

    return strategies


def generate_strategies(
    llm: LLMInterface,
    scaffolder_prompt_config: ScaffolderPromptConfig,
    num_strategies: int,
) -> List[str]:
    """Generate diverse problem-solving strategies.

    Args:
        llm: LLM instance for generating strategies
        scaffolder_prompt_template: Full scaffolder prompt with 'YOUR STRATEGY HERE' placeholder
        num_strategies: Number of strategies to generate

    Returns:
        List of strategy descriptions to use in scaffold generation

    Raises:
        ValueError: If strategy generation or parsing fails
    """
    prompt = _build_strategy_prompt(scaffolder_prompt_config, num_strategies)
    response = llm.generate_response(prompt)
    return _parse_numbered_strategies(response.content)
