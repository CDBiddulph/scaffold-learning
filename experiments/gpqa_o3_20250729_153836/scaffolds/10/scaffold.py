import logging
import re
from typing import Optional
from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)
CHOICE_PATTERN = re.compile(r"\b([A-D])\b")


def _query_llm(question: str, retries: int = 2) -> str:
    """
    Ask the LLM for the answer letter (A–D) to the provided multiple-choice question.
    The LLM is instructed to think silently and return ONLY one of the letters.
    """
    system_prompt = (
        "You are an expert problem-solver. The user will give you ONE multiple-choice "
        "question whose options are labelled A), B), C) and D).\n"
        "1. Think through the problem step-by-step internally (do NOT reveal this).\n"
        "2. Output EXACTLY one capital letter (A, B, C or D) on a single line.\n"
        "3. Do NOT add explanations, punctuation, or extra words.\n"
        "Remember: the final output must be only the letter."
    )

    user_prompt = f"Question:\n{question}\n\nAnswer:"
    for attempt in range(retries + 1):
        logging.info(f"LLM attempt {attempt + 1} / {retries + 1}")
        try:
            response = execute_llm(user_prompt, system_prompt=system_prompt)
        except Exception as e:
            logging.error(f"LLM call failed: {e}")
            continue

        logging.debug(f"Raw LLM response:\n{response}")

        match = CHOICE_PATTERN.search(response.strip())
        if match:
            letter = match.group(1)
            logging.info(f"Parsed answer letter: {letter}")
            return letter

        logging.warning(f"Unable to parse a valid letter from response: {response!r}")

    raise ValueError("Failed to obtain a valid answer letter from LLM.")


def process_input(input_string: str) -> str:
    """
    Main entry point required by the grader.

    Parameters
    ----------
    input_string : str
        The full text of the multiple-choice question.

    Returns
    -------
    str
        Exactly one of the letters 'A', 'B', 'C', or 'D'.
    """
    try:
        return _query_llm(input_string)
    except Exception as exc:
        # If everything fails, log the error and default to a safe guess
        logging.error(f"process_input encountered an error: {exc}")
        # A deterministic fallback so behaviour is predictable
        return "A"