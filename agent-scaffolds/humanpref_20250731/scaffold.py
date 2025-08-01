import logging
import time
from llm_executor import execute_llm


def evaluate_responses(input_string: str):
    """Use LLM to evaluate which response is better"""

    evaluation_prompt = f"""You are evaluating two responses to determine which one is better. Use these criteria in order of importance:

1. INSTRUCTION FOLLOWING: Does it do what was actually asked? Follow specific requirements?
2. ACCURACY: Is the information correct and factual?
3. COMPLETENESS: Does it provide adequate information without being excessive?
4. HELPFULNESS: Is it useful to someone who asked this question?
5. CLARITY: Is it well-organized and easy to understand?

{input_string}"""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()

        # Extract final answer - try multiple patterns
        if result.endswith("A"):
            return "A"
        elif result.endswith("B"):
            return "B"
        elif "ANSWER: A" in result.upper():
            return "A"
        elif "ANSWER: B" in result.upper():
            return "B"
        elif result.startswith("A"):
            return "A"
        elif result.startswith("B"):
            return "B"
        elif "A" in result and "B" not in result:
            return "A"
        elif "B" in result and "A" not in result:
            return "B"

        logging.warning(f"LLM returned unexpected result: {result}")
        return "A"  # Default fallback

    except Exception as e:
        logging.error(f"Error in LLM evaluation: {e}")
        return "A"  # Default fallback


def process_input(input_string: str) -> str:
    try:
        # Evaluate which response is better
        result = evaluate_responses(input_string)

        logging.info(f"Evaluation result: {result}")
        return result

    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback
