import logging
import re
from typing import Optional

from llm_executor import execute_llm   # provided by the evaluation harness


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def _ask_llm(question: str, retries: int = 2) -> Optional[str]:
    """
    Sends the MC-question to the LLM and tries to extract the single-letter answer.
    Retries a few times if the answer cannot be parsed.
    """
    system_prompt = (
        "You are a concise multiple-choice solver.  "
        "Think step-by-step internally, but in your final reply output ONLY the single capital "
        "letter that corresponds to the best answer (A, B, C, or D).  "
        "Do NOT output anything else."
    )

    user_prompt = f"QUESTION:\n{question}\n\nRemember: final reply = A or B or C or D."

    for attempt in range(retries + 1):
        try:
            LOGGER.info(f"Asking LLM (attempt {attempt + 1}/{retries + 1})")
            raw_response = execute_llm(user_prompt, system_prompt=system_prompt).strip()
            LOGGER.info(f"Raw LLM response: {raw_response!r}")

            # Extract the first standalone capital letter A–D
            match = re.search(r"\b([ABCD])\b", raw_response)
            if match:
                return match.group(1)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Error while querying LLM", exc_info=exc)

    return None


def process_input(input_string: str) -> str:
    """
    Main entry point required by the autograder.
    Receives the raw input (which already contains the choices) and returns the single letter.
    """
    answer = _ask_llm(input_string)

    if answer is None:
        # Hard fail-safe: when LLM parsing fails, default to 'A'
        LOGGER.error("Failed to parse a valid answer from LLM – defaulting to 'A'")
        answer = "A"

    return answer