import logging
import os
import re
import time
from typing import Optional

from llm_executor import execute_llm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_CALLS = 3                 # how many times we will try to query the LLM
TIMEOUT_BUFFER = 15           # seconds reserved to shut down gracefully
MODEL_INSTRUCTIONS = (
    "You will be shown a multiple-choice problem whose answer is exactly one "
    "capital letter (A, B, C or D).\n"
    "1. Think step-by-step silently.\n"
    "2. At the end, print ONLY the single letter of the option you choose.\n"
    "3. Do NOT print anything else – no prefix like 'Answer:', no explanation, "
    "no punctuation, just the bare letter.\n"
    "If you are unsure, still pick the best choice.\n"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
LETTER_PATTERN = re.compile(r"\b([A-D])\b")


def _extract_letter(text: str) -> Optional[str]:
    """
    Finds the first isolated capital letter A–D in the text and returns it.
    """
    match = LETTER_PATTERN.search(text.strip())
    return match.group(1) if match else None


def _ask_llm(question: str, remaining_time: float) -> Optional[str]:
    """
    Query the LLM once and try to extract the answer letter.
    """
    try:
        # Guard against pathological long questions that might blow past timeout.
        # The scoring harness allows 120 s total, we leave TIMEOUT_BUFFER seconds
        # at the end for shutdown.
        start = time.time()
        response = execute_llm(
            prompt=question,
            system_prompt=MODEL_INSTRUCTIONS
        )
        logging.info(f"LLM raw response:\n{response}")
        letter = _extract_letter(response)
        if letter:
            logging.info(f"Extracted letter: {letter}")
        else:
            logging.warning("Failed to extract a valid answer letter.")
        return letter
    except Exception as exc:
        logging.error(f"LLM call failed: {exc}")
        return None
    finally:
        elapsed = time.time() - start
        logging.info(f"LLM round-trip took {elapsed:.2f} s. "
                     f"~{remaining_time - elapsed:.2f} s remain.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def process_input(input_string: str) -> str:
    """
    Core function required by the evaluation harness.

    It simply passes the entire input to the LLM together with minimal
    instructions, tries a few times, and returns the single-letter answer.
    """
    logging.basicConfig(level=logging.INFO)

    hard_deadline = time.time() + 120 - TIMEOUT_BUFFER
    for attempt in range(1, MAX_CALLS + 1):
        logging.info(f"LLM attempt {attempt}/{MAX_CALLS}")
        remaining = hard_deadline - time.time()
        if remaining <= 0:
            logging.error("Timeout budget exhausted before finishing queries.")
            break

        letter = _ask_llm(input_string, remaining)
        if letter:
            return letter

    # Fallback: if we could not parse an answer, default to 'A'
    logging.error("All attempts failed – defaulting to 'A'.")
    return "A"