import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _extract_first_choice(text: str) -> Optional[str]:
    """
    Look for the first standalone capital letter (A-Z) in the LLM response.
    """
    match = re.search(r"\b([A-Z])\b", text)
    if match:
        return match.group(1)
    return None


def _query_llm(question: str, retries: int = 2, timeout: float = 90.0) -> str:
    """
    Ask the LLM for the answer.  Retry a few times if parsing fails.
    """
    system_prompt = (
        "You are an expert tutor.  Carefully solve the problem that will be given "
        "by the user.  After your reasoning, output ONLY the single capital letter "
        "that corresponds to the correct multiple-choice answer.  "
        "Do not output any extra words, explanation, or punctuation—just the letter."
    )

    for attempt in range(1, retries + 2):
        start_time = time.time()
        logger.info(f"LLM attempt {attempt} of {retries + 1}")

        response = execute_llm(question, system_prompt=system_prompt)

        logger.debug(f"Raw LLM response:\n{response}")

        letter = _extract_first_choice(response)
        if letter and letter in ALLOWED_LETTERS:
            logger.info(f"Parsed choice '{letter}' from LLM response.")
            return letter

        elapsed = time.time() - start_time
        logger.warning(
            f"Attempt {attempt}: Failed to parse a valid choice in {elapsed:.2f} s. "
            f"Response was: {response!r}"
        )

    raise ValueError("LLM did not return a valid answer letter after retries.")


def process_input(input_string: str) -> str:
    """
    Main entry point required by the evaluator.
    Receives the entire prompt (including any metadata) and must return the chosen letter.
    """
    # Ensure we don't run over the global time limit
    overall_start = time.time()
    try:
        answer_letter = _query_llm(input_string)
        return answer_letter
    finally:
        logger.info(f"Total processing time: {time.time() - overall_start:.2f} s")