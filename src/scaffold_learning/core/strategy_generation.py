"""Generate diverse problem-solving strategies for scaffold creation."""

from typing import List

from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.llm_response_utils import extract_json_dict
from scaffold_learning.core.data_structures import ScaffolderPromptConfig
from scaffold_learning.core.scaffolder_prompt_builder import build_scaffolder_prompt


_STRATEGY_INSTRUCTIONS = """Your job is to create strategies for scaffolder LLMs. The full prompt that will be sent to the scaffolder LLMs is shown above. Please generate diverse strategies, ready to be inserted in place of "YOUR STRATEGY HERE" in that prompt. Each strategy will be sent to a different scaffolder LLM, which will then implement a scaffold based on that strategy.

Each strategy should describe a different approach or methodology for solving the problem. The strategies should provide specific guidance on how to approach the problem.

Your score will be the maximum score achieved by any generated scaffold. Therefore, it doesn't matter if some of your strategies end up failing, as long as at least one is very successful. However, you shouldn't use a strategy unless you think it has a chance of being the best one. Act like a shrewd investor who knows when to diversify their portfolio and when to commit. (You're different from a traditional investor in that you're not trying to maximize your overall return on investment, but rather the return of your single best bet.)

Each strategy should contain clear instructions (1-5 sentences) providing comprehensive guidance on how to implement the scaffold. Each scaffolder LLM will see the prompt above and a single strategy from your list; they won't see the other strategies you generated, so each strategy must be self-contained and complete. It's possible that the strategies will overlap significantly in content, especially if there are many strategies (e.g. more than ~5). For example, you might end up with some strategies that are exactly the same for 4 sentences and only differ in the last sentence. That is only an example, though - you should reason carefully about exactly how to balance exploration and exploitation to maximize your overall score. Even if many strategies are requested, don't write shorter strategies for this reason; all of the strategies should be sufficiently detailed for the scaffolder LLM to understand what to do.

Return your strategies as a JSON object with 0-indexed string keys, like this:
{{
  "0": "First strategy description here",
  "1": "Second strategy description here",
  "2": "Third strategy description here"
}}"""


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
    strategies_dict = extract_json_dict(response)

    # Extract strategies in the order they appear in the dict (ignore keys completely)
    strategies = []
    for value in strategies_dict.values():
        if not isinstance(value, str):
            raise ValueError(
                f"Expected string strategy but got {type(value).__name__}: {value}"
            )
        strategies.append(value)

    if not strategies:
        raise ValueError(f"No strategies found in JSON:\n{strategies_dict}")

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
