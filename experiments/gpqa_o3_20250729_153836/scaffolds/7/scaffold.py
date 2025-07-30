import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
LLM_SYSTEM_PROMPT = (
    "You are an expert problem-solver.  You receive ONE multiple-choice question "
    "and must choose A, B, C, or D.  Think step-by-step, but in the very last "
    "line write exactly:  Answer: <letter>  (e.g. Answer: B).\n"
    "Do not add anything after that final line."
)

TIME_LIMIT_SECS = 110          # Give ourselves a safety margin (< 120 s limit)
CALL_TIMEOUT_SECS = 60         # Max time we allow for the LLM call itself
LOG_LEVEL = logging.INFO
# --------------------------------------------------------------------------- #

logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s | %(message)s")


def _query_llm(question: str) -> str:
    """
    Ask the LLM to solve the MCQ contained in *question*.
    Returns whatever the LLM responded.
    """
    start = time.time()
    logging.info("Sending question to LLM …")

    try:
        response: str = execute_llm(
            prompt=question,
            system_prompt=LLM_SYSTEM_PROMPT,
        )
    except Exception as exc:
        logging.error(f"LLM call failed: {exc}")
        raise

    elapsed = time.time() - start
    logging.info(f"LLM answered in {elapsed:0.1f} s")
    return response


def _extract_letter(raw_response: str) -> Optional[str]:
    """
    Pull the choice letter out of the LLM output.
    Looks for the last occurrence of the pattern   Answer: X
    where X is A–D  (case-insensitive).
    """
    matches = re.findall(r"Answer:\s*([ABCD])\b", raw_response, flags=re.I)
    if not matches:
        return None
    # Take the last match (in case the model rambled)
    return matches[-1].upper()


def process_input(input_string: str) -> str:
    """
    Main entry point required by the grader.
    Receives the raw prompt (including metadata tags) and must return ONLY the
    chosen letter (A/B/C/D).  Any other text will count as wrong.
    """
    time_start = time.time()

    try:
        llm_response = _query_llm(input_string)
        letter = _extract_letter(llm_response)
        if letter is None:
            logging.warning("Failed to locate 'Answer: <letter>' pattern; "
                            "trying a more permissive search.")
            # Fallback: first standalone A-D capital letter line
            simple = re.findall(r"^\s*([ABCD])\s*$", llm_response, flags=re.M)
            letter = simple[-1].upper() if simple else None

        if letter not in {"A", "B", "C", "D"}:
            raise ValueError(f"Could not extract a valid option from LLM output:\n{llm_response}")

        return letter

    except Exception as exc:
        logging.error(f"process_input failed: {exc}")
        # If something goes terribly wrong, guess 'A' to avoid empty output
        return "A"

    finally:
        total = time.time() - time_start
        logging.info(f"Total wall-clock time: {total:0.1f} s")